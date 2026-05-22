import os
from typing import List, Optional
from packages.rag_core.data.chunking import chunk_text, normalize_text
from packages.rag_core.models.embeddings import EmbeddingClient
from packages.rag_core.utils import config
from packages.rag_core.utils.logger import logger
from math import sqrt

from langchain_chroma import Chroma
from langchain_core.documents import Document

import chromadb

from PyPDF2 import PdfReader


from packages.rag_core.data.marker import extract_text_with_marker

def read_pdf(path: str) -> list[str]:
    reader = PdfReader(path)
    text = []
    for page in reader.pages:
        t = page.extract_text()
        text.append(t or "")
    return [normalize_text(p) for p in text]


def load_file_to_text(path: str, force_ocr: bool = None) -> list[str]:
    ext = os.path.splitext(path)[1].lower()
    use_marker_ocr = config.FORCE_MARKER_OCR if force_ocr is None else force_ocr

    if ext != ".pdf":
        raise ValueError(f"Solo se soportan archivos PDF. Extensión recibida: {ext}")

    raw_text = read_pdf(path)
    if use_marker_ocr:
        joined = "\n".join([p or "" for p in raw_text]) if isinstance(raw_text, list) else (raw_text or "")
        if len(joined) < config.MARKER_OCR_THRESHOLD:
            ocr_result = extract_text_with_marker(path, force_ocr=True)
            if isinstance(ocr_result, list):
                return ocr_result
            if '\f' in ocr_result:
                return [p for p in ocr_result.split('\f')]
            return [p.strip() for p in ocr_result.split('\n\n')]
    return raw_text

def ingest_files(
    paths: List[str],
    collection_name: str = None,
    persist: bool = None,
    dry_run: bool = False,
    dedup_threshold: float = None,
    force_ocr: bool = None,
    extract_graph: bool = None
):
    """
    Ingiere archivos PDF en ChromaDB y opcionalmente extrae relaciones al grafo RDF.
    
    Args:
        paths: Lista de rutas a archivos PDF.
        collection_name: Nombre de la colección ChromaDB.
        persist: Si persistir en disco.
        dry_run: Si solo simular sin guardar.
        dedup_threshold: Umbral de similitud para deduplicación.
        force_ocr: Forzar uso de OCR para extracción.
        extract_graph: Extraer relaciones al grafo de conocimiento.
                      Por defecto usa config.GRAPH_EXTRACT_ON_INGEST.
    
    Returns:
        Lista de documentos procesados.
    """
    def clean_text(text):
        return text.encode('utf-8', 'ignore').decode('utf-8')
    
    collection_name = collection_name or config.DEFAULT_COLLECTION_NAME
    extract_graph = config.GRAPH_EXTRACT_ON_INGEST if extract_graph is None else extract_graph
    
    emb = EmbeddingClient()

    chroma_host = os.environ.get("CHROMA_HOST", "saga-chromadb")

    persistent_client = chromadb.HttpClient(host=chroma_host, port=8000)

    vectordb = Chroma(
        client=persistent_client,
        collection_name=collection_name,
        embedding_function=emb._client
    )
    persist = config.DEFAULT_PERSIST if persist is None else persist
    dedup_threshold = config.DEDUP_SIM_THRESHOLD if dedup_threshold is None else dedup_threshold
    
    # Inicializar extractor de grafo si está habilitado
    graph_store = None
    relation_extractor = None
    if extract_graph and not dry_run:
        try:
            from packages.rag_core.knowledge_graph.graph_store import GraphStore
            from packages.rag_core.knowledge_graph.extract_relations import RelationExtractor
            graph_store = GraphStore().open()
            relation_extractor = RelationExtractor()
            logger.info("Extracción de grafo habilitada")
        except ImportError as e:
            logger.warning(f"No se pudo inicializar el grafo de conocimiento: {e}")
            extract_graph = False
    
    documents = []
    chunks_for_graph = []  # Chunks a procesar para el grafo
    seen_hashes = set()
    seen_embeddings = []
    
    for path in paths:
        text = load_file_to_text(path, force_ocr=force_ocr)
        if isinstance(text, list):
            combined_text = "\n".join([p or "" for p in text])
            if not combined_text.strip():
                logger.info(f"No text extracted from {path}, skipping.")
                continue
        else:
            if not text or len(text.strip()) == 0:
                logger.info(f"No text extracted from {path}, skipping.")
                continue

        try:
            chroma_collection = persistent_client.get_collection(name=collection_name)
        except Exception as col_err:
            logger.warning(f"No se pudo obtener la colección nativa para validación: {col_err}")
            chroma_collection = None

        chunks = chunk_text(text, chunk_size_chars=config.CHUNK_DEFAULT_SIZE, chunk_overlap=config.CHUNK_DEFAULT_OVERLAP)
        for i, ch in enumerate(chunks):
            ch_dict = ch if isinstance(ch, dict) else {"text": ch}
            ch_text = ch_dict.get("text") or ""
            ch_clean = clean_text(ch_text)

            if not ch_clean.strip():
                logger.info(f"Skipping empty or whitespace-only chunk for {path} (chunk {i})")
                continue

            import hashlib
            chunk_hash = hashlib.sha1(ch_clean.encode("utf-8")).hexdigest()[:12]
            chunk_id = f"chunk_{os.path.basename(path).replace('.', '_')}_{i}_{chunk_hash}"
            if chroma_collection is not None:
                try:
                    res = chroma_collection.get(ids=[chunk_id])
                    # Si el arreglo 'ids' contiene elementos, significa que ya está en el disco
                    if res and len(res.get("ids", [])) > 0:
                        logger.info(f"--> [DB MATCH] El chunk '{chunk_id}' ya existe en ChromaDB. Omitiendo cálculo de embedding.")
                        continue
                except Exception as db_check_err:
                    logger.warning(f"Error preventivo en consulta nativa del ID {chunk_id}: {db_check_err}")

            h = hash(ch_clean)
            if h in seen_hashes:
                logger.info(f"Skipping exact-duplicate chunk for {path} (chunk {i})")
                continue

            accept = True
            q_emb = None
            if dedup_threshold and dedup_threshold < 1.0:
                # Calcular embedding una sola vez para este chunk y reutilizarlo
                q_emb = emb.embed(ch_clean)
                for d_emb in seen_embeddings:
                    dot = sum(a * b for a, b in zip(q_emb, d_emb))
                    norm_q = sqrt(sum(a * a for a in q_emb))
                    norm_d = sqrt(sum(a * a for a in d_emb))
                    sim = dot / (norm_q * norm_d) if norm_q and norm_d else 0.0
                    if sim >= dedup_threshold:
                        accept = False
                        logger.info(f"Skipping near-duplicate chunk for {path} (chunk {i}) sim={sim:.3f})")
                        break

            if not accept:
                continue

            seen_hashes.add(h)
            if q_emb is not None:
                seen_embeddings.append(q_emb)

            metadata = {"source": os.path.basename(path), "chunk": i}
            if ch_dict.get("page_start") is not None:
                metadata.update({"page_start": ch_dict.get("page_start"), "page_end": ch_dict.get("page_end")})
            if ch_dict.get("char_start") is not None:
                metadata.update({"char_start": ch_dict.get("char_start"), "char_end": ch_dict.get("char_end")})
            
            # Generar ID único para el chunk
            metadata["chunk_id"] = chunk_id
            
            documents.append(Document(page_content=ch_clean, metadata=metadata))
            
            # Preparar chunk para extracción de grafo
            if extract_graph:
                chunks_for_graph.append({
                    "text": ch_clean,
                    "chunk_id": chunk_id,
                    "source": os.path.basename(path),
                    "page": ch_dict.get("page_start")
                })

    docs_insertados = []

    if documents:
        if dry_run or not persist:
            mode = "Dry-run" if dry_run else "Non-persistent"
            logger.info(f"{mode} ingest: {len(documents)} documents would be added to collection '{collection_name}'")
            return documents
        else:
            logger.info(f"Indexando {len(documents)} fragmentos en ChromaDB de forma segura...")
            # chunk por chunk para aislar anomalías de la API externa
            for idx, doc in enumerate(documents):
                try:
                    target_id = doc.metadata.get("chunk_id")

                    vectordb.add_documents([doc], ids=[target_id])
                    docs_insertados.append(doc)
                except Exception as chunk_err:
                    logger.error(f"[X] Omitiendo chunk {idx} debido a una anomalía o filtro de la API de Google: {chunk_err}")
                    logger.error(f"Texto conflictivo: {doc.page_content[:100]}...")
            
            logger.info(f"Ingesta finalizada: {len(docs_insertados)}/{len(documents)} guardados en ChromaDB.")
            
            # Extraer relaciones al grafo de conocimiento 
            if extract_graph and relation_extractor and graph_store and chunks_for_graph:
                logger.info(f"Extrayendo relaciones de {len(chunks_for_graph)} chunks al grafo...")
                try:
                    processed, triples = relation_extractor.extract_batch(
                        chunks_for_graph,
                        store=graph_store
                    )
                    logger.info(f"Grafo actualizado: {processed} chunks → {triples} tripletas")
                except Exception as e:
                    logger.error(f"Error extrayendo relaciones: {e}")
                finally:
                    graph_store.close()
    else:
        logger.info("No documents to add after processing (dedup/filter may have removed all chunks)")
    
    # Solo los que realmente se insertaron para que las métricas del BUS sean reales
    return docs_insertados
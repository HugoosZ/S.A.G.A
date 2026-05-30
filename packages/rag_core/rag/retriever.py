import os
import chromadb
from math import sqrt
from typing import List
from langchain_core.documents import Document
from langchain_chroma import Chroma
from packages.rag_core.models.embeddings import EmbeddingClient
from packages.rag_core.utils import config
from packages.rag_core.utils.logger import logger

def get_vectorstore(collection_name: str = None) -> Chroma:
    """
    Se conecta al contenedor de ChromaDB por red HTTP y devuelve el vectorstore de LangChain.
    """
    col_name = collection_name or getattr(config, 'DEFAULT_COLLECTION_NAME', 'study_collection')
    emb = EmbeddingClient()
    
    # Conexión al contenedor Docker vía red bridge
    chroma_host = os.environ.get("CHROMA_HOST", "saga-chromadb")
    persistent_client = chromadb.HttpClient(host=chroma_host, port=8000)
    
    vectordb = Chroma(
        client=persistent_client,
        collection_name=col_name,
        embedding_function=emb._client
    )
    return vectordb

def get_relevant_docs(query: str, k: int = None, collection_name: str = None) -> List[Document]:
    """
    Recupera fragmentos relevantes y aplica reranking por similitud de coseno si está habilitado.
    """
    k = k or getattr(config, 'DEFAULT_TOP_K', 4)
    vectordb = get_vectorstore(collection_name=collection_name)
    
    rerank_enabled = getattr(config, 'RERANK_ENABLED', False)
    top_n = getattr(config, 'RERANK_TOP_K', 10) if rerank_enabled else k

    retriever = vectordb.as_retriever(search_kwargs={"k": top_n})

    # LangChain 0.1+ recomienda invoke()
    if hasattr(retriever, "invoke"):
        candidates = retriever.invoke(query)
    else:
        candidates = retriever.get_relevant_documents(query)

    if not candidates:
        logger.info(f"No se recuperaron documentos para la query: {query}")
        return []

    if not rerank_enabled or k >= top_n:
        selected = candidates[:k]
        logger.info(f"Retornando los {len(selected)} mejores candidatos sin reranking.")
        return selected

    # ==========================================
    # LÓGICA DE RERANKING OPTIMIZADA POR RED
    # ==========================================
    scored = []
    emb_client = EmbeddingClient()
    
    # 1. Calculamos el embedding de la pregunta del usuario
    q_emb = emb_client.embed([query])
    if isinstance(q_emb, list) and len(q_emb) == 1:
        q_emb = q_emb[0]

    # 2. Obtenemos el cliente nativo HTTP para extraer los vectores en milisegundos
    chroma_host = os.environ.get("CHROMA_HOST", "saga-chromadb")
    persistent_client = chromadb.HttpClient(host=chroma_host, port=8000)
    
    try:
        native_collection = persistent_client.get_collection(name=vectordb._collection.name)
    except Exception as e:
        logger.warning(f"No se pudo obtener colección nativa para rerank, fallando elegantemente: {e}")
        native_collection = None

    cached_embeddings = {}
    if native_collection is not None:
        candidate_ids = [
            (getattr(doc, 'metadata', {}) or {}).get('chunk_id')
            for doc in candidates
        ]
        candidate_ids = [doc_id for doc_id in candidate_ids if doc_id]
        if candidate_ids:
            try:
                resp = native_collection.get(ids=candidate_ids, include=['embeddings'])
                ids = resp.get('ids') or []
                embeddings = resp.get('embeddings') or []
                cached_embeddings = {
                    doc_id: emb for doc_id, emb in zip(ids, embeddings) if emb is not None
                }
            except Exception as db_err:
                logger.debug(f"Error al extraer embeddings por lote: {db_err}")

    # 3. Emparejamiento y cálculo de Distancia de Coseno
    for doc in candidates:
        meta = getattr(doc, 'metadata', {}) or {}
        d_emb = None

        # a) Prioridad 1: Buscar si LangChain ya adjuntó el embedding
        if meta.get('embedding'):
            d_emb = meta.get('embedding')

        # b) Prioridad 2: Buscar el vector nativo en BD usando el chunk_id exacto (¡Costo $0 y ultra rápido!)
        if d_emb is None and native_collection is not None:
            doc_id = meta.get('chunk_id')
            if doc_id and doc_id in cached_embeddings:
                d_emb = cached_embeddings[doc_id]

        # c) Prioridad 3: Fallback (Solo si todo lo anterior falla, recalcula con Gemini)
        if d_emb is None:
            doc_text = getattr(doc, 'page_content', '')
            logger.warning(f"Recalculando embedding de fallback para reranking...")
            d_emb = emb_client.embed([doc_text])
            if isinstance(d_emb, list) and len(d_emb) == 1:
                d_emb = d_emb[0]

        # Similitud del Coseno matemática pura
        dot = sum(a * b for a, b in zip(q_emb, d_emb))
        norm_q = sqrt(sum(a * a for a in q_emb))
        norm_d = sqrt(sum(a * a for a in d_emb))
        score = dot / (norm_q * norm_d) if norm_q and norm_d else 0.0
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [doc for _, doc in scored[:k]]
    logger.info(f"Reranking completado. Retornando {len(selected)} documentos finales.")
    
    return selected
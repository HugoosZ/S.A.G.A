from packages.rag_core.rag.retriever import get_relevant_docs, get_vectorstore
from packages.rag_core.models.llm import Agent
from packages.rag_core.utils import config
from packages.rag_core.utils.logger import logger
from typing import Dict, Any, Tuple, List, Set
import tiktoken
import re

llm = Agent()

SYSTEM_INSTRUCTIONS = (
    "Eres un asistente virtual de la Secretaría de Estudios de la Universidad Diego Portales (UDP). Tu rol es actuar como el primer filtro "
    "para las consultas de los estudiantes.\n"
    "REGLAS DE RESPUESTA:\n"
    "1. Temas académicos/administrativos con info en contexto: Responde de manera clara, precisa y amable basándote estrictamente en los documentos.\n"
    "2. Temas académicos/administrativos complejos: Si la información requerida no está en los reglamentos o depende netamente de intervención humana (ej. revisión de un caso particular, excepciones, firmas), DEBES iniciar tu respuesta exactamente con: 'DERIVAR A SECRETARIA' y explicar brevemente el motivo.\n"
    "3. Vida Universitaria UDP (ej. cafeterías, ubicaciones, Starbucks cercano a la facultad): Si la pregunta es sobre la vida cotidiana pero ligada a la UDP o sus sedes, respóndela amablemente. Puedes usar tu conocimiento general si la información no está en el contexto. NO derives a la secretaria.\n"
    "4. Consultas completamente ajenas a la UDP: Si te piden crear código de programación, preguntar por el clima, o temas que no tienen ninguna relación con la vida universitaria o la UDP, rechaza la solicitud amablemente explicando que tu función es exclusiva para temas de la universidad. NO derives a la secretaria.\n"
    "JAMÁS inventes reglas o políticas académicas que no estén en el texto proporcionado."
)

FILE_EXTENSIONS = {".pdf"}

def extract_mentioned_files(question: str, available_sources: Set[str]) -> List[str]:
    mentioned = []
    question_lower = question.lower()
    
    file_pattern = r'[\w\-\.]+(?:' + '|'.join(re.escape(ext) for ext in FILE_EXTENSIONS) + r')'
    explicit_files = re.findall(file_pattern, question_lower)
    mentioned.extend(explicit_files)
    
    for source in available_sources:
        source_lower = source.lower()
        base_name = re.sub(r'\.[^.]+$', '', source_lower)
        if base_name and len(base_name) > 2:
            pattern = r'\b' + re.escape(base_name) + r'\b'
            if re.search(pattern, question_lower):
                mentioned.append(source_lower)
    
    context_patterns = [
        r'(?:en|del|según|from|in)\s+(?:el\s+)?(?:archivo|documento|libro|pdf|file)\s+["\']?([\w\-\.]+)["\']?',
        r'(?:archivo|documento|libro|pdf|file)\s+["\']?([\w\-\.]+)["\']?',
    ]
    for pattern in context_patterns:
        matches = re.findall(pattern, question_lower)
        for match in matches:
            for source in available_sources:
                if match in source.lower() or source.lower().startswith(match):
                    mentioned.append(source.lower())
                    break
    
    seen = set()
    unique_mentioned = []
    for f in mentioned:
        if f not in seen:
            seen.add(f)
            unique_mentioned.append(f)
    
    return unique_mentioned

def prioritize_docs_by_source(context_docs: List, files_focus: List[str]) -> List:
    if not files_focus:
        return context_docs
    
    focus_set = set(f.lower() for f in files_focus)
    prioritized = []
    others = []
    
    for d in context_docs:
        meta = d.metadata if hasattr(d, "metadata") else {}
        src = (meta.get("source") or "").lower()
        if src in focus_set:
            prioritized.append(d)
        else:
            others.append(d)
    
    logger.info(f"Priorización de documentos: {len(prioritized)} prioritarios, {len(others)} otros")
    return prioritized + others

def build_prompt(context_docs, question: str) -> str:
    max_model_tokens = getattr(config, 'MAX_MODEL_TOKENS', 4000)
    reserved = getattr(config, 'RESERVED_RESPONSE_TOKENS', 1000)
    context_texts = []

    base_suffix = f"\n\nPregunta del estudiante:\n{question}\n\nRespuesta (en español):"
    base_prefix = SYSTEM_INSTRUCTIONS + "\n\nContexto normativo recuperado:\n"

    # CORRECCIÓN TIKTOKEN: Usamos 'cl100k_base' genérico para evitar errores con el nombre de Gemini
    encoding = tiktoken.get_encoding("cl100k_base")

    base_tokens = len(encoding.encode(SYSTEM_INSTRUCTIONS + base_suffix))
    allowed_tokens_for_context = max_model_tokens - reserved - base_tokens
    if allowed_tokens_for_context <= 0:
        allowed_tokens_for_context = max_model_tokens // 4

    used_tokens = 0
    for i, d in enumerate(context_docs):
        meta = d.metadata if hasattr(d, 'metadata') else {}
        header = f"[Reglamento/Documento: {meta.get('source','desconocido')} | fragmento={meta.get('chunk', i)}]\n"
        content = d.page_content or ""
        tok_count = len(encoding.encode(header + content))

        if used_tokens + tok_count > allowed_tokens_for_context:
            remaining = allowed_tokens_for_context - used_tokens
            if remaining <= 0:
                break
            lo, hi = 0, len(content)
            best = 0
            while lo <= hi:
                mid = (lo + hi) // 2
                if len(encoding.encode(header + content[:mid])) <= remaining:
                    best = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            if best > 0:
                truncated = content[:best]
                context_texts.append(f"{header}{truncated}")
                used_tokens += len(encoding.encode(header + truncated))
            break
        else:
            context_texts.append(f"{header}{content}")
            used_tokens += tok_count

    context_block = "\n\n---\n\n".join(context_texts) if context_texts else ""

    formatting = (
        "Instrucciones de formato:\n"
        "1. Si la consulta es académica y falta información o requiere intervención humana, inicia exactamente con 'DERIVAR A SECRETARIA'.\n"
        "2. Si la consulta es trivial pero de la UDP (ej. cafeterías), usa tu conocimiento general para responder y NO derives a secretaría.\n"
        "3. Si la consulta es ajena a la UDP (ej. hacer código, clima), indícale amablemente tu propósito y NO derives a secretaría.\n"
        "4. Si usas información de los reglamentos, incluye al final una sección 'FUENTES'.\n"
        "5. Mantén un tono formal, amable e institucional.\n"
    )

    prompt = (
        f"{SYSTEM_INSTRUCTIONS}\n\nContexto normativo recuperado:\n{context_block}\n\n{formatting}\nPregunta del estudiante:\n{question}\n\nRespuesta (en español):"
    )
    return prompt

def build_hybrid_prompt(hybrid_context: str, question: str) -> str:
    formatting = (
        "Instrucciones de formato:\n"
        "- Usa los hechos estructurados del grafo y los textos para responder consultas académicas.\n"
        "- Si la consulta académica requiere decisión humana o falta contexto, inicia exactamente con 'DERIVAR A SECRETARIA'.\n"
        "- Si la consulta es de vida universitaria UDP (ej. cafeterías), respóndela con tu conocimiento general y NO derives a secretaría.\n"
        "- Si es ajena a la UDP (ej. código, clima), aclara tu propósito y NO derives a secretaría.\n"
        "- Incluye una sección 'FUENTES' con los reglamentos consultados si das una respuesta resolutiva basada en los textos.\n"
    )
    prompt = (
        f"{SYSTEM_INSTRUCTIONS}\n\nContexto normativo y estructurado:\n{hybrid_context}\n\n{formatting}\n"
        f"Pregunta del estudiante:\n{question}\n\nRespuesta (en español):"
    )
    return prompt

def answer_with_rag(question: str, k: int = None, collection_name: str = None, use_hybrid: bool = None) -> Dict[str, Any]:
    use_hybrid = getattr(config, 'GRAPH_HYBRID_SEARCH', False) if use_hybrid is None else use_hybrid
    
    if use_hybrid:
        try:
            from packages.rag_core.knowledge_graph.hybrid_retriever import HybridRetriever
            from packages.rag_core.knowledge_graph.graph_store import GraphStore
            
            graph_store = GraphStore()
            graph_store.open()
            hybrid = HybridRetriever(graph_store=graph_store, collection_name=collection_name)
            result = hybrid.retrieve(question, k=k)
            graph_store.close()
            
            if result.has_structural or result.vector_docs:
                prompt = build_hybrid_prompt(result.combined_context, question)
                encoding = tiktoken.get_encoding("cl100k_base")
                tokens_used = len(encoding.encode(prompt))
                
                answer = llm.generate(prompt)
                
                return {
                    "answer": answer,
                    "source_documents": result.enriched_docs,
                    "tokens_used": tokens_used,
                    "files_focus": [],
                    "query_type": result.query_type,
                    "has_structural": result.has_structural,
                    "sources_used": result.sources_used
                }
        except ImportError:
            logger.debug("Módulo de grafo no disponible, usando búsqueda vectorial estándar")
        except Exception as e:
            logger.warning(f"Error en búsqueda híbrida, fallback a vectorial: {e}")
    
    docs = get_relevant_docs(question, k=k, collection_name=collection_name)
    
    available_sources = set()
    for d in docs:
        meta = d.metadata if hasattr(d, "metadata") else {}
        src = meta.get("source")
        if src:
            available_sources.add(src)
    
    mentioned_files = extract_mentioned_files(question, available_sources)
    
    if mentioned_files:
        logger.info(f"Archivos mencionados detectados: {mentioned_files}")
        docs = prioritize_docs_by_source(docs, mentioned_files)
    
    prompt = build_prompt(docs, question)
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens_used = len(encoding.encode(prompt))

    answer = llm.generate(prompt)
    return {
        "answer": answer,
        "source_documents": docs,
        "tokens_used": tokens_used,
        "files_focus": mentioned_files,
        "query_type": "vector_only",
        "has_structural": False,
        "sources_used": ["chroma_db"]
    }
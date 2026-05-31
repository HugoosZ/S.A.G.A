from typing import Dict, Any, Tuple, Optional
import json
import tiktoken

from langchain.agents import initialize_agent, Tool
from packages.rag_core.knowledge_graph.hybrid_retriever import get_hybrid_retriever
from packages.rag_core.knowledge_graph.graph_store import GraphStore
from packages.rag_core.models.llm import Agent
from packages.rag_core.utils import config
from packages.rag_core.utils.logger import logger

llm = Agent()

def create_react_agent(k: int = None, max_iterations: int = 3, budget: Optional[Dict[str, int]] = None, verbose: bool = True):
    """
    Crea un agente ReAct equipado con la herramienta de búsqueda híbrida (Grafo + Vector).
    """
    # 1. Inicializar el motor híbrido
    graph_store = GraphStore()
    graph_store.open()
    hybrid_retriever = get_hybrid_retriever(graph_store=graph_store)

    llm_client = llm._client
    
    # 2. Configurar cálculo offline de tokens para Gemini
    encoding = tiktoken.get_encoding("cl100k_base")

    # 3. Estado local para este request específico (Thread-Safe)
    state = {"calls": 0, "tokens": 0}
    max_calls = budget.get('max_calls') if budget else getattr(config, 'BUDGET_CALLS_PER_QUERY', 5)
    token_budget = budget.get('token_budget') if budget else getattr(config, 'TOKEN_BUDGET_PER_QUERY', 10000)

    # 4. Definir la herramienta (Tool) del Agente
    def saga_search_tool(query: str) -> str:
        """Herramienta que el Agente usará para buscar información en SAGA."""
        state['calls'] += 1
        
        if state['calls'] > max_calls:
            return "ERROR: Límite de búsquedas alcanzado. Responde con la información que ya tienes."
            
        est_tokens = len(encoding.encode(query))
        state['tokens'] += est_tokens
        
        if state['tokens'] > token_budget:
            return "ERROR: Presupuesto de tokens agotado. Responde con la información que ya tienes."

        logger.info(f"[Agente ReAct] Buscando en Grafo+Vectores: '{query}'")
        
        # Recuperación Híbrida
        result = hybrid_retriever.retrieve(query, k=k or getattr(config, 'DEFAULT_TOP_K', 4))
        
        # Le entregamos el contexto crudo al LLM para que él lo analice
        return result.combined_context

    # Configuración de las herramientas para LangChain
    tools = [
        Tool(
            name="SAGA_Knowledge_Search",
            func=saga_search_tool,
            description="Útil para buscar información académica de la universidad. Úsala para buscar ramos, evaluaciones, fechas, reglamentos o pre-requisitos. Formula consultas muy específicas."
        )
    ]

    # 5. Inicializar Agente
    agent_executor = initialize_agent(
        tools,
        llm_client,
        agent="zero-shot-react-description",
        verbose=verbose,
        max_iterations=max_iterations,
        handle_parsing_errors=True # Vital para que Gemini no crashee si formatea mal su pensamiento
    )

    return agent_executor, state, graph_store

def run_react_agent(question: str, k: int = None, max_iterations: int = 4, budget: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """
    Ejecuta el agente ReAct y formatea la salida para el microservicio.
    """
    agent_executor, state, graph_store = create_react_agent(
        k=k, 
        max_iterations=max_iterations, 
        budget=budget, 
        verbose=True
    )
    
    try:
        # El agente comienza su ciclo de pensamiento (Thought -> Action -> Observation)
        final_answer = agent_executor.run(question)
    except Exception as e:
        logger.error(f"Error en la ejecución del Agente ReAct: {e}")
        final_answer = f"Ocurrió un error en el razonamiento del agente: {e}"
    finally:
        # Aseguramos cerrar la conexión al Grafo
        graph_store.close()

    # Retornamos el payload estandarizado para el BUS
    return {
        "answer": final_answer,
        "calls_used": state["calls"],
        "tokens_used": state["tokens"],
        "query_type": "react_agent_hybrid"
    }
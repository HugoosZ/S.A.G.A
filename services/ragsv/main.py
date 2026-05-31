import sys
import os
import json
import traceback

# 1. Forzar a Python a mirar la raíz del monorepo (/app dentro del contenedor)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from shared.service_base import start_service
from packages.rag_core.rag.qa import answer_with_rag
from packages.rag_core.utils.logger import logger

def process_request(payload: dict) -> dict:
    """
    Procesa las peticiones entrantes del BUS.
    La arquitectura base ya convierte el JSON a dict (entrada)
    y espera un dict de vuelta (salida).
    """
    try:
        # payload ya es un dict, no necesitamos json.loads()
        question = payload.get("question")
        
        if not question:
            return {
                "status": "error",
                "message": "El payload debe contener la clave 'question'."
            }
            
        logger.info(f"Procesando pregunta: '{question}'")
        
        # Seleccionamos el motor cognitivo a usar (por defecto el RAG estándar)
        engine = payload.get("engine", "standard")
        
        if engine == "react":
            from packages.rag_core.rag.ReAct import run_react_agent
            result = run_react_agent(
                question=question,
                k=payload.get("k")
            )
        else:
            result = answer_with_rag(
                question=question,
                k=payload.get("k"),
                collection_name=payload.get("collection_name")
            )
        
        # Devolvemos un dict nativo, la librería lo convierte a string JSON
        return {
            "status": "success",
            "answer": result.get("answer"),
            "tokens_used": result.get("tokens_used"),
            "query_type": result.get("query_type"),
            "calls_used": result.get("calls_used"),
            "sources_used": result.get("sources_used", []),
            "files_focus": result.get("files_focus", [])
        }
        
    except Exception as e:
        logger.error(f"Error interno en ragsv: {e}\n{traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Error interno del servidor: {str(e)}"
        }

if __name__ == "__main__":
    logger.info("Iniciando servicio de Generación Aumentada (RAGSV)...")
    # Registra el servicio en el BUS con la taxonomía oficial de 5 letras
    start_service("ragsv", process_request)
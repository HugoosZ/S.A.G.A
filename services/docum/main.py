import sys
import os

# Asegurar que el contenedor reconozca la raíz del monorepo para las importaciones
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from shared.service_base import start_service
from packages.rag_core.data.ingestion import ingest_files

SERVICE_NAME = "docum"

def procesar_ingesta_pdf(payload):
    """
    Función de procesamiento callback para el service_base.
    Recibe el diccionario ya parseado y debe retornar un diccionario.
    """
    ruta_pdf = payload.get("file_path")
    
    if not ruta_pdf:
        return {"status": "error", "message": "Falta el parámetro 'file_path' en el payload JSON."}
        
    if os.path.exists(ruta_pdf):
        print(f"[{SERVICE_NAME.upper()}] Ingestando de forma incremental en ChromaDB: {ruta_pdf}")
        # Lógica nativa heredada de RAGent
        processed_docs = ingest_files(paths=[ruta_pdf])
        return {"status": "success", "chunks_agregados": len(processed_docs)}
    else:
        return {"status": "error", "message": f"El archivo especificado no existe en el sistema: {ruta_pdf}"}

if __name__ == "__main__":
    start_service(SERVICE_NAME, procesar_ingesta_pdf)
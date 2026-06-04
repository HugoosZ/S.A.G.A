# services/recep/main.py

import json
import logging
from shared.mail_db import init_db
from shared.service_base import start_service
from repository import save_email, build_conversation 
from utils import (
    validate_email_data,
    normalizar_email_data,
    asignar_hilo,
    is_valid_email_content
)

SERVICE_NAME = "recep"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)


def process_email(data: dict) -> dict:
    """Procesa el correo entrante y genera el texto para el RAG"""
    try:
        if not validate_email_data(data):
            logger.warning("Datos de correo no válidos: %s", data)
            return {"status": "error", "message": "Invalid email data"}

        if not is_valid_email_content(data):
            logger.info("Correo filtrado (Spam/Irrelevante): %s", data.get("subject"))
            return {"status": "ignored", "message": "Spam or irrelevant content"}

        # Normalizar y resolver hilos en memoria técnica
        normalized_data = normalizar_email_data(data)
        email_with_thread = asignar_hilo(normalized_data)

        # Persistir en PostgreSQL
        save_email(email_with_thread)
        
        # Reconstruir la historia cronológica desde la DB para el RAG
        hilo_id_real = email_with_thread.get("hilo_id")
        conversation = build_conversation(hilo_id_real)
        messages = conversation.get("messages", [])

        # Construir el bloque plano de historial 
        history_blocks = []
        for msg in messages:
            block = f"De: {msg['sender']}\nFecha: {msg['timestamp']}\nMensaje: {msg['body']}"
            history_blocks.append(block)
        full_history_text = "\n\n".join(history_blocks)

        # Extraer el último mensaje 
        latest_msg = messages[-1] if messages else {}

        logger.info(
            "Contrato RAG generado exitosamente para el hilo: %s", 
            hilo_id_real
        )

        # Retornamos el contrato final optimizado para el Bus
        return {
            "status": "success",
            "action": "process_rag",
            "metadata": {
                "thread_id": hilo_id_real,
                "total_messages": len(messages),
                "last_sender": email_with_thread.get("sender"),
                "subject_clean": email_with_thread.get("subject")
            },
            "rag_payload": {
                "latest_message": {
                    "sender": latest_msg.get("sender"),
                    "body": latest_msg.get("body"),
                    "timestamp": latest_msg.get("timestamp")
                },
                "full_history_text": full_history_text
            }
        }

    except Exception as e:
        logger.error("Error procesando correo en recep: %s", str(e))
        return {
            "status": "error",
            "message": str(e)
        }


def run():
    init_db()  
    start_service(SERVICE_NAME, process_email)


if __name__ == "__main__":
    run()
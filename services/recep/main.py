import json
import logging
import smtplib
from email.mime.text import MIMEText
import os
import sys
import time

# El contenedor arranca con `python -m services.recep.main`
# Ponemos también este directorio en sys.path para los imports planos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prometheus_client import start_http_server, Histogram

from shared.mail_db import init_db
from shared.service_base import start_service
from repository import save_email, build_conversation 
from shared.soa_lib import connect_to_bus, send_message
from utils import (
    validate_email_data,
    normalizar_email_data,
    asignar_hilo,
    is_valid_email_content
)

SERVICE_NAME = "recep"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)

RECEP_LATENCY = Histogram('recep_processing_latency_seconds', 'Time spent processing incoming emails in RECEP')

def enviar_respuesta_smtp(data: dict) -> dict:
    """Se conecta al servidor SMTP de Gmail y despacha la respuesta manteniendo el hilo"""
    destinatario = data.get("to")
    cuerpo_mensaje = data.get("body")
    asunto_original = data.get("subject", "Consulta Secretaría de Estudios")
    in_reply_to = data.get("in_reply_to")
    references = data.get("references")
    
    remitente = os.getenv("EMAIL_USUARIO")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not remitente or not password:
        logger.error("Credenciales SMTP no configuradas en el entorno.")
        return {"status": "error", "message": "Credenciales SMTP faltantes"}

    try:
        msg = MIMEText(cuerpo_mensaje)
        msg['Subject'] = f"Re: {asunto_original}"
        msg['From'] = remitente
        msg['To'] = destinatario
        
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Correo enviado exitosamente a {destinatario} en el hilo {references}")
        return {"status": "success", "message": "Correo despachado"}
    except Exception as e:
        logger.error(f"Fallo al enviar correo SMTP: {e}")
        return {"status": "error", "message": str(e)}

@RECEP_LATENCY.time()
def process_email(data: dict) -> dict:
    """Procesa peticiones del bus: Ingestar correos nuevos o Enviar respuestas"""
    start_timestamp = time.time()
    
    # 1. INTERCEPTAR ORDEN DE ENVÍO SMTP
    if data.get("action") == "enviar_correo":
        return enviar_respuesta_smtp(data)
        
    # 2. FLUJO NORMAL DE LECTURA Y CONTEXTUALIZACIÓN
    try:
        if not validate_email_data(data):
            logger.warning("Datos de correo no válidos: %s", data)
            return {"status": "error", "message": "Invalid email data"}

        if not is_valid_email_content(data):
            logger.info("Correo filtrado (Spam/Irrelevante): %s", data.get("subject"))
            return {"status": "ignored", "message": "Spam or irrelevant content"}

        normalized_data = normalizar_email_data(data)
        email_with_thread = asignar_hilo(normalized_data)

        save_email(email_with_thread)
        
        hilo_id_real = email_with_thread.get("hilo_id")
        conversation = build_conversation(hilo_id_real)
        messages = conversation.get("messages", [])

        history_blocks = []
        for msg in messages:
            block = f"De: {msg['sender']}\nFecha: {msg['timestamp']}\nMensaje: {msg['body']}"
            history_blocks.append(block)
        full_history_text = "\n\n".join(history_blocks)

        latest_msg = messages[-1] if messages else {}
        timestamp_val = latest_msg.get("timestamp")
        if timestamp_val is not None and not isinstance(timestamp_val, str):
            timestamp_val = timestamp_val.isoformat() 

        logger.info("Contrato RAG generado exitosamente para el hilo: %s", hilo_id_real)

        contrato_final = {
            "metadata": {
                "thread_id": hilo_id_real,
                "last_sender": email_with_thread.get("sender"),
                "subject_clean": email_with_thread.get("subject"),
                "message_id": email_with_thread.get("message_id"),
                "ingestion_timestamp": start_timestamp
            },
            "rag_payload": {
                "latest_message": {
                    "body": latest_msg.get("body"),
                    "timestamp": timestamp_val 
                },
                "full_history_text": full_history_text
            }
        }

        bus_host = os.getenv("BUS_HOST", "saga-bus")
        bus_port = int(os.getenv("BUS_PORT", 5000))
        sock_class = connect_to_bus(bus_host, bus_port)
        
        if sock_class:
            send_message(sock_class, "class", json.dumps(contrato_final))
            sock_class.close()
            logger.info(f"Contrato RAG del hilo {hilo_id_real} derivado a CLASIFICACIÓN.")

        return {"status": "success", "message": "Procesado y derivado a clasificación"}

    except Exception as e:
        logger.error("Error procesando correo en recep: %s", str(e))
        return {
            "status": "error",
            "message": str(e)
        }

def run():
    init_db()  
    start_http_server(8002)
    logger.info("Servidor de métricas Prometheus iniciado en el puerto 8002")
    start_service(SERVICE_NAME, process_email)

if __name__ == "__main__":
    run()
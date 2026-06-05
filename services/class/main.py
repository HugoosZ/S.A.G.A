import sys
import os
import json
import logging

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from shared.service_base import start_service
from shared.soa_lib import connect_to_bus, send_message, receive_message

SERVICE_NAME = "class"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)

def process_classification(payload: dict) -> dict:
    """Recibe el contrato de recep, arma el prompt, consulta a RAGSV y enruta."""
    try:
        metadata = payload.get("metadata", {})
        rag_payload = payload.get("rag_payload", {})
        hilo_id = metadata.get("thread_id")
        correo_alumno = metadata.get("last_sender")

        # 1. Ensamblar Prompt
        prompt_enriquecido = f"""
        Eres un asistente académico de la Secretaría de Estudios.
        Responde la duda del estudiante basándote estrictamente en tu base de conocimiento RAG.
        Si la solicitud exige intervención humana (ej. anular ramo, justificar inasistencia médica), responde exactamente con la frase: REQUIERE_DERIVACION.
        
        Historial de conversación: {rag_payload.get("full_history_text", "")}
        Pregunta actual: {rag_payload.get("latest_message", {}).get("body", "")}
        """

        # 2. Consultar a RAGSV
        bus_host = os.getenv("BUS_HOST", "saga-bus")
        bus_port = int(os.getenv("BUS_PORT", 5000))
        sock = connect_to_bus(bus_host, bus_port)
        
        req_ragsv = {"question": prompt_enriquecido}
        send_message(sock, "ragsv", json.dumps(req_ragsv))
        resp_ragsv_bytes = receive_message(sock)
        
        respuesta_ia = ""
        if resp_ragsv_bytes:
            datos_ragsv = json.loads(resp_ragsv_bytes[7:].decode("utf-8", errors="ignore"))
            respuesta_ia = datos_ragsv.get("answer", "")

        # 3. Enrutamiento (La lógica de decisión)
        if "REQUIERE_DERIVACION" in respuesta_ia:
            logger.info(f"Clasificación: El hilo {hilo_id} requiere derivación humana.")
            req_casos = {
                "action": "derivar",
                "thread_id": hilo_id,
                "correo_usuario": correo_alumno,
                "motivo": "Trámite administrativo estricto detectado por LLM."
            }
            send_message(sock, "casos", json.dumps(req_casos))
            receive_message(sock)
        else:
            logger.info(f"Clasificación: Consulta resuelta. Enviando a correos y cerrando caso.")
            
            # Avisar a Casos que se resolvió automáticamente
            req_casos = {"action": "cambiar_estado", "thread_id": hilo_id, "nuevo_estado": "resuelto_auto"}
            send_message(sock, "casos", json.dumps(req_casos))
            receive_message(sock)

            # Aquí se delegaría de vuelta a RECEP para enviar el correo (Endpoint POST /emails/send del informe)
            # send_message(sock, "recep", json.dumps({"action": "enviar_correo", "to": correo_alumno, "body": respuesta_ia}))
            logger.info(f"Se ha ordenado el envío de la respuesta a {correo_alumno}.")

        sock.close()
        return {"status": "success", "message": "Clasificación y orquestación finalizada."}

    except Exception as e:
        logger.error(f"Error en clasificación: {e}")
        return {"status": "error", "message": str(e)}

def run():
    logger.info("Iniciando Servicio de Clasificación con LLM...")
    start_service(SERVICE_NAME, process_classification)

if __name__ == "__main__":
    run()
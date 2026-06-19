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
        
        # 3.0 Asegurar que la respuesta no sea nula y limpiar espacios
        respuesta_ia = (respuesta_ia or "").strip()
        respuesta_upper = respuesta_ia.upper()

        # 3.1 Nueva condición: Derivar si hay palabras clave O si la IA está vacía
        if not respuesta_ia or "REQUIERE_DERIVACION" in respuesta_upper or "DERIVAR A SECRETARIA" in respuesta_upper:
            logger.info(f"Clasificación: El hilo {hilo_id} requiere derivación humana (o la IA no supo responder).")
            
            req_casos = {
                "action": "derivar",
                "thread_id": hilo_id,
                "correo_usuario": correo_alumno,
                "motivo": f"Derivación por IA o falta de información. Respuesta obtenida: {respuesta_ia[:100]}"
            }
            send_message(sock, "casos", json.dumps(req_casos))
            receive_message(sock)

            # Enviar correo de aviso al estudiante manteniendo el hilo
            message_id = metadata.get("message_id")
            asunto_limpio = metadata.get("subject_clean", "Consulta Secretaría de Estudios")
            
            mensaje_aviso = (
                "Estimado/a estudiante,\n\n"
                "Su consulta requiere la revisión de antecedentes académicos o un trámite administrativo específico, "
                "por lo que ha sido derivada a la Secretaría de Estudios.\n\n"
                "Un profesional de nuestro equipo analizará su caso particular y se pondrá en contacto "
                "con usted a la brevedad respondiendo a este mismo correo.\n\n"
                "Atentamente,\nSistema Automático S.A.G.A."
            )

            orden_envio_aviso = {
                "action": "enviar_correo", 
                "to": correo_alumno, 
                "body": mensaje_aviso,
                "subject": asunto_limpio,
                "in_reply_to": message_id,
                "references": hilo_id
            }
            send_message(sock, "recep", json.dumps(orden_envio_aviso))
            logger.info(f"Se ha enviado el aviso de derivación a {correo_alumno}.")

        else:
            logger.info(f"Clasificación: Consulta resuelta. Enviando a correos y cerrando caso.")
            
            # Avisar a Casos que se resolvió automáticamente
            req_casos = {"action": "cambiar_estado", "thread_id": hilo_id, "nuevo_estado": "resuelto_auto"}
            send_message(sock, "casos", json.dumps(req_casos))
            receive_message(sock)

            message_id = metadata.get("message_id")
            asunto_limpio = metadata.get("subject_clean", "Consulta Secretaría de Estudios")
            
            orden_envio = {
                "action": "enviar_correo", 
                "to": correo_alumno, 
                "body": respuesta_ia,
                "subject": asunto_limpio,
                "in_reply_to": message_id,   # ID exacto del mensaje que estamos respondiendo
                "references": hilo_id        # ID de la raíz del hilo
            }
            send_message(sock, "recep", json.dumps(orden_envio))
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
import logging
import json
from shared.service_base import start_service
import repository as repo

# Librerias para enviar los mensajes al ragsv
import os
from shared.soa_lib import connect_to_bus, send_message, receive_message

SERVICE_NAME = "casos"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)

def process_case_request(payload: dict) -> dict:
    'Procesa la solicitud de caso y devuelve la respuesta con la prioridad calculada'
    try: 
        action = payload.get("action")
        thread_id = payload.get("thread_id")
        correo_usuario = payload.get("correo_usuario")

        if not thread_id:
            return {"status": "error", "message": "Falta thread_id en la solicitud"}
        
        if action == "derivar":
            motivo = payload.get("motivo", "Derivado por el clasificador.")
            if not correo_usuario:
                return {"status": "error", "message": "Falta correo_usuario para la acción de derivar"}
            result = repo.derivar_a_secretaría(thread_id, correo_usuario, motivo)
            logger.info(f"caso_derivado: Hilo {thread_id} asignado a SECRETARÍA con Prioridad [{result['prioridad']}]")

            return {"status": "success", "action": "derivar",  "data": result}

        elif action == "cambiar_estado":
            nuevo_estado = payload.get("nuevo_estado")
            motivo = payload.get("motivo", "")

            exito = repo.cambiar_estado_caso(thread_id, nuevo_estado, motivo)
            if exito:
                logger.info(f"estado_cambiado: Hilo {thread_id} cambiado a estado [{nuevo_estado}]")
                return {"status": "success", "action": "cambiar_estado", "data": {"thread_id": thread_id, "nuevo_estado": nuevo_estado}}
            return {"status": "error", "message": "No se pudo cambiar el estado del caso"}

        else:
            return {"status": "error", "message": "Acción no reconocida"}

    except Exception as e:
        logger.error(f"Error al procesar la solicitud: {e}")
        return {"status": "error", "message": "Error interno del servicio"}



# Función para consultar al RAGSV desde este servicio de casos, si es necesario 
def consultar_ia_ragsv(pregunta_texto: str) -> dict:
    """
    Actúa como cliente del bus para enviar una consulta al servicio RAGSV
    y esperar su respuesta cognitiva.
    """
    sock = None
    try:
        # 1. Leer credenciales del bus desde el entorno
        bus_host = os.getenv("BUS_HOST", "saga-bus")
        bus_port = int(os.getenv("BUS_PORT", 5000))
        
        # 2. Conectar al bus
        sock = connect_to_bus(bus_host, bus_port)
        if not sock:
            return {"status": "error", "message": "No se pudo conectar al bus"}

        # 3. Armar el contrato exacto que exige ragsv.py
        payload_dict = {
            "question": pregunta_texto
        }
        
        # 4. Enviar al servicio destino "ragsv"
        send_message(sock, "ragsv", json.dumps(payload_dict))
        
        # 5. Esperar la respuesta
        response_bytes = receive_message(sock)
        
        if response_bytes:
            # El bus devuelve 5 bytes de servicio + 2 bytes de status + payload
            payload_raw = response_bytes[7:].decode("utf-8", errors="ignore")
            return json.loads(payload_raw)
        else:
            return {"status": "error", "message": "Timeout esperando al RAGSV"}

    except Exception as e:
        logger.error(f"Error enrutando hacia ragsv: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if sock:
            sock.close()

def run():
    logger.info(f"Iniciando servicio {SERVICE_NAME}...")
    repo.init_casos_db()
    start_service(SERVICE_NAME, process_case_request)

if __name__ == "__main__":
    run()
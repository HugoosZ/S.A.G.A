import logging
import json
from shared.service_base import start_service
import repository as repo

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

def run():
    logger.info(f"Iniciando servicio {SERVICE_NAME}...")
    repo.init_casos_db()
    start_service(SERVICE_NAME, process_case_request)

if __name__ == "__main__":
    run()
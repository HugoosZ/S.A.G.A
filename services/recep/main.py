# services/recep/main.py

import json
import logging

from shared.service_base import start_service
from shared.soa_lib import send_message

from utils import (
    validate_email_data,
    normalizar_email_data,
    asignar_hilo
)

SERVICE_NAME = "recep"
NEXT_SERVICE = "class"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)


def process_email(data: dict) -> dict:
    """Función que procesa el correo"""

    try:

        if not validate_email_data(data):
            logger.warning("Datos de correo no válidos: %s", data)
            return {"status": "error", "message": "Invalid email data"}

        normalized_data = normalizar_email_data(data)

        email_with_thread = asignar_hilo(normalized_data)

        logger.info(
            "Correo procesado: %s",
            email_with_thread.get("message_id")
        )


        
        return email_with_thread


    except Exception as e:
        logger.error("Error procesando correo: %s", str(e))
        return {
            "status": "error",
            "message": str(e)
        }


def run():
    start_service(SERVICE_NAME, process_email)


if __name__ == "__main__":
    run()
import json
from soa_lib import connect_to_bus, send_message, receive_message


def start_service(service_name, process_function):
    """
    Esta es una plantilla base para todos los servicios de SAGA, para respetar las reglas impuestas en soa_lib.py
    service_name: str de exactamente 5 caracteres (ej. 'recep', 'class').
    process_function: Función que recibe un dict (petición) y retorna un dict (respuesta).
    """
    if len(service_name) != 5:
        raise ValueError(
            f"El nombre del servicio debe tener exactamente 5 caracteres. Recibido: '{service_name}'")

    sock = connect_to_bus()
    try:
        print(f"[{service_name.upper()}] Registrando servicio...")
        send_message(sock, "sinit", service_name)

        init_data = receive_message(sock)
        print(f"[{service_name.upper()}] Confirmación del Bus: {init_data!r}")
        print(f"[{service_name.upper()}] Listo para recibir peticiones JSON.\n")

        while True:
            data = receive_message(sock)
            if not data:
                print(f"[{service_name.upper()}] Desconectado del Bus.")
                break

            # extrae el payload omitiendo los 5 caracteres de enrutamiento
            raw_payload = data[5:].decode('utf-8', errors='ignore')

            try:
                # convierte el payload que está en formato JSON a un diccionario de Python
                request_data = json.loads(raw_payload)

                # se le entrega los datos para trabajar a la función X que se vaya a crear en cada servicio, y se espera que retorne un diccionario con la respuesta
                response_data = process_function(request_data)

                # valida que la respuesta efectivamente sea un diccionario según el esquema
                if not isinstance(response_data, dict):
                    raise ValueError(
                        "La función de procesamiento debe retornar un diccionario.")

            except json.JSONDecodeError:
                response_data = {
                    "status": "error",
                    "error_type": "ParseError",
                    "message": "El payload recibido no es un JSON válido."
                }
            except Exception as e:
                response_data = {
                    "status": "error",
                    "error_type": "ServerError",
                    "message": str(e)
                }

            # devuelve la respuesta al Bus convirtiendo el diccionario a un string JSON
            # proceso inverso al de arriba
            response_str = json.dumps(response_data)
            send_message(sock, service_name, response_str)

    except Exception as e:
        print(f"[{service_name.upper()}] Error crítico en la conexión: {e}")
    finally:
        print(f"[{service_name.upper()}] Cerrando socket.")
        sock.close()

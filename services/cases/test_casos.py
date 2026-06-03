import json
import time
from shared.soa_lib import connect_to_bus, send_message, receive_message

def enviar_a_casos(payload_dict):
    """
    Función auxiliar para conectar al bus y enviar el mensaje 
    formateado al servicio 'casos'
    """
    try:
        sock = connect_to_bus("localhost", 5001)
        payload_json = json.dumps(payload_dict)
        
        print(f"Enviando al servicio 'casos': {payload_dict['action']}")

        send_message(sock, "casos", payload_json)
        response = receive_message(sock)
        
        if response:
            print("RESPUESTA RAW:", response.decode())
        sock.close()
        print("Mensaje enviado con éxito.")
        
    except Exception as e:
        print(f"Error al conectar o enviar al Bus: {e}")

if __name__ == "__main__":
    print("=== SIMULADOR DE CLASIFICADOR / BUS CENTRAL ===")
    # -------------------------------------------------------------
    # ESCENARIO 1: Primer intento de un alumno (Prioridad debería ser BAJA)
    # -------------------------------------------------------------
    correo_alumno = "alumno_prueba@udp.cl"
    hilo_1 = "thread_001_id"
    
    payload_1 = {
        "action": "derivar",
        "thread_id": hilo_1,
        "correo_usuario": correo_alumno,
        "motivo": "Solicitud de tercera oportunidad para ramo de programación."
    }
    
    enviar_a_casos(payload_1)
    time.sleep(3)
    
    # -------------------------------------------------------------
    # ESCENARIO 2: El mismo alumno insiste (Prioridad debería subir a MEDIA)
    # -------------------------------------------------------------
    hilo_2 = "thread_002_id"
    payload_2 = {
        "action": "derivar",
        "thread_id": hilo_2,
        "correo_usuario": correo_alumno,
        "motivo": "Reitera tercera oportunidad: Adjunta historial académico previo."
    }
    
    enviar_a_casos(payload_2)
    
    print("\n=== SIMULACIÓN FINALIZADA ===")
    print("Revisa tu terminal del servicio 'casos' y las tablas en tu Postgres.")
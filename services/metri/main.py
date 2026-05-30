from shared.soa_lib import connect_to_bus, send_message, receive_message
import json

def iniciar_servicio_metricas():
    sock = connect_to_bus()
    
    try:
        # 1. Registro inicial en el bus
        print("Registrando servicio 'metri'...")
        send_message(sock, "sinit", "metri")
        
        # 2. Confirmación de conexión
        init_data = receive_message(sock)
        print(f"Confirmación de bus recibida: {init_data!r}")
        print("Servicio de Métricas y Auditoría en línea y esperando eventos.\n")
        
        # 3. Bucle de procesamiento de métricas
        while True:
            data = receive_message(sock)
            if not data:
                print("Conexión cerrada por el bus de integración.")
                break
                
            # Extraer la carga útil (payload) omitiendo los 5 caracteres de la cabecera
            payload = data[5:].decode()
            print(f"Métrica entrante: '{payload}'")
            
            try:
                # Aquí se integra la lógica interna: almacenamiento en BD, cálculo de KPIs, etc.
                datos_metrica = json.loads(payload)
                print("Procesando evento de auditoría...")
                
                # Respuesta de confirmación al componente que emitió el evento
                send_message(sock, "metri", "ACK: Métrica registrada exitosamente")
                
            except json.JSONDecodeError:
                print("Error: El formato de la métrica no es un JSON válido.")
                send_message(sock, "metri", "ERR: Formato JSON incorrecto")
                
    except Exception as e:
        print(f"Falla crítica en el servicio de métricas: {e}")
    finally:
        print("Finalizando conexión del servicio 'metri'.")
        sock.close()

if __name__ == "__main__":
    iniciar_servicio_metricas()
from shared.soa_lib import connect_to_bus, send_message, receive_message
import time

def iniciar_agente_monitor():
    sock = connect_to_bus()
    
    try:
        print("Agente Monitor de Correo inicializado en segundo plano.")
        
        # Bucle continuo de monitoreo
        while True:
            print("Consultando bandeja de entrada institucional...")
            
            # Lógica ficticia: Reemplace esto con la conexión real IMAP/API de correo
            hay_nuevo_correo = False 
            
            if hay_nuevo_correo:
                # Se extrae asunto, cuerpo y metadatos relevantes
                payload_correo = '{"remitente": "estudiante@mail.udp.cl", "asunto": "Consulta malla"}'
                
                # Se transmite el mensaje capturado hacia el servicio de Recepción (ej. 'recep')
                print("Nuevo correo detectado. Transmitiendo al bus (Servicio 'recep')...")
                send_message(sock, "recep", payload_correo)
                
                # Esperar y procesar la confirmación del ESB
                respuesta_bus = receive_message(sock)
                if respuesta_bus:
                    # Se omiten los 5 caracteres correspondientes al identificador del servicio
                    print(f"Confirmación del servicio de recepción: {respuesta_bus[5:].decode()}")
                    
                    # Opcionalmente, se puede notificar también al servicio de métricas ('metri')
                    send_message(sock, "metri", '{"evento": "correo_recibido", "estado": "exito"}')
                    receive_message(sock) # Consumir respuesta de 'metri'
            
            # Frecuencia de chequeo (polling) para evitar saturación
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\nInterrupción manual del agente detectada.")
    except Exception as e:
        # En caso de error, emitir notificación al servicio de métricas
        print(f"Error en el agente monitor: {e}")
        send_message(sock, "metri", f'{{"evento": "error_monitor", "detalle": "{str(e)}"}}')
    finally:
        print("Cerrando conexión del Agente Monitor.")
        sock.close()

if __name__ == "__main__":
    iniciar_agente_monitor()
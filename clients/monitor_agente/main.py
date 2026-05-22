import os
import time
import json
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv

# Importación corregida apuntando a shared
from shared.soa_lib import connect_to_bus, send_message, receive_message

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER", "cuenta_prueba_udp@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "contrasena")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")

BUS_HOST = os.getenv("BUS_HOST", "soa-bus")
BUS_PORT = int(os.getenv("BUS_PORT", "5000"))
TIEMPO_ESPERA = int(os.getenv("TIEMPO_ESPERA", "30"))

#Función para hacer pruebaas
def procesar_bandeja_entrada(sock):
    """Simula la lectura de un correo y el envío directo de la métrica."""
    print("Simulando procesamiento de un correo entrante...")
    
    # métrica ficticia
    payload_metrica = {
        "evento": "procesamiento_simulado",
        "id_correo": 9999,
        "tiempo_procesamiento_segundos": 1.25,
        "codigo_http_resultado": 200
    }
    
    # Enviar al servicio de métricas
    print("Enviando datos al servicio 'metri'...")
    send_message(sock, "metri", json.dumps(payload_metrica))
    
    # Lee respuesta del servicio de métricas para liberar el socket
    respuesta = receive_message(sock)
    if respuesta:
        
        print(f"Confirmación recibida: {respuesta[5:].decode('utf-8', errors='ignore')}")


''''
def procesar_bandeja_entrada(sock):
    """Conecta al correo, extrae mensajes no leídos y los envía al bus."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        status, mensajes = mail.search(None, "UNREAD")
        lista_ids = mensajes[0].split()

        for num in lista_ids:
            status, data = mail.fetch(num, "(RFC822)")
            
            asunto = ""
            remitente = ""
            cuerpo = ""

            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    asunto_raw, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(asunto_raw, bytes):
                        asunto = asunto_raw.decode(encoding if encoding else "utf-8")
                    else:
                        asunto = asunto_raw
                        
                    remitente = msg.get("From")
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                cuerpo = part.get_payload(decode=True).decode()
                                break
                    else:
                        cuerpo = msg.get_payload(decode=True).decode()
            
            print(f"Procesando correo real de: {remitente}")

            payload_correo = {
                "id_correo": int(num.decode()),
                "remitente": remitente,
                "asunto": asunto,
                "cuerpo": cuerpo
            }
            mensaje_str = json.dumps(payload_correo)

            # Envío a Clasificación (IA)
            tiempo_inicio = time.time()
            send_message(sock, "class", mensaje_str)
            
            print("Esperando clasificación...")
            respuesta_class = receive_message(sock)
            
            tiempo_total = time.time() - tiempo_inicio
            estado = 200 if respuesta_class else 500

            # Envío a Métricas
            payload_metrica = {
                "evento": "procesamiento_correo",
                "id_correo": payload_correo["id_correo"],
                "tiempo_procesamiento_segundos": tiempo_total,
                "codigo_http_resultado": estado
            }
            send_message(sock, "metri", json.dumps(payload_metrica))
            
            # Limpieza del buffer
            receive_message(sock)

        mail.logout()
    except Exception as e:
        print(f"Error en procesamiento de correos: {e}")
        '''

if __name__ == "__main__":
    print("Iniciando Agente Monitor de SAGA...")
    
    
    sock = connect_to_bus(host=BUS_HOST, port=BUS_PORT)
    
    try:
        while True:
            procesar_bandeja_entrada(sock)
            print(f"Esperando {TIEMPO_ESPERA} segundos...\n")
            time.sleep(TIEMPO_ESPERA)
    finally:
        print("Cerrando conexión del Agente.")
        sock.close()
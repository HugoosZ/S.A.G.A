import json
import time
import logging
from imapclient import IMAPClient
import email
from email.header import decode_header
import re
from shared.soa_lib import connect_to_bus, send_message, receive_message


# CONFIGURACIÓN
IMAP_HOST = "imap.gmail.com"
EMAIL_ACCOUNT = "poner correo "
EMAIL_PASSWORD = "contraseña de aplicación"  # IMPORTANTE: Usar contraseña de aplicación, no la contraseña normal del correo
BUS_HOST = "localhost"
BUS_PORT = 5000

SERVICE_TARGET = "recep"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitor_agente")


def decode_mime_words(s):
    """Decodifica headers tipo =?UTF-8?..."""
    decoded = decode_header(s)
    return ''.join([
        str(t[0], t[1] or 'utf-8') if isinstance(t[0], bytes) else t[0]
        for t in decoded
    ])


def clean_reply_history(body: str) -> str:
    """
    Elimina el historial de correos anteriores citados en una respuesta (limpieza de hilos).
    Evita enviar payloads gigantescos que desbordan los buffers del ESB.
    """
    if not body:
        return ""
        
    
    patterns = [
        r"(?i)El\s+[\w\s,]+a\s+las\s+\d+:\d+,\s+.*?\s+escribi\u00f3:", 
        r"(?i)On\s+[\w\s,]+\s+at\s+\d+:\d+,\s+.*?\s+wrote:",         
        r"-----Mensaje original-----",
        r"-----Original Message-----",
        r"________________________________",
        r"(?i)^De:\s+.*@.*",
        r"(?i)^From:\s+.*@.*"
    ]
    
    lines = body.splitlines()
    cleaned_lines = []
    
    for line in lines:
        # Si la línea coincide con un inicio de historial de respuestas, dejamos de leer
        if any(re.search(p, line) for p in patterns):
            break
        if line.strip().startswith('>'):
            continue
        cleaned_lines.append(line)
        
    cleaned_body = "\n".join(cleaned_lines).strip()
    
    MAX_BODY_CHARS = 3000
    if len(cleaned_body) > MAX_BODY_CHARS:
        cleaned_body = cleaned_body[:MAX_BODY_CHARS] + "... [Texto truncado por tamaño]"
        
    return cleaned_body


def extract_body(msg):
    """Extrae cuerpo del correo (soporta multipart) y poda el historial de hilos"""
    raw_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                raw_body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        raw_body = msg.get_payload(decode=True).decode(errors="ignore")

    
    return clean_reply_history(raw_body)

def fetch_unseen_emails():
    """Obtiene correos no leídos que cumplan con el filtro de asunto específico"""
    try:
        with IMAPClient(IMAP_HOST) as client:
            client.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            client.select_folder("INBOX")

            filtro_asunto = "Consulta de prueba SAGA"
            messages = client.search(["UNSEEN", "SUBJECT", filtro_asunto])
            
            if not messages:
                return []
                
            response = client.fetch(messages, ["RFC822"])

            emails = []
            for msgid, data in response.items():
                raw_email = data[b"RFC822"]
                msg = email.message_from_bytes(raw_email)

                subject = decode_mime_words(msg.get("Subject", ""))
                sender = msg.get("From", "")
                body = extract_body(msg)

                payload = {
                    "sender": sender,
                    "subject": subject,
                    "body": body,
                    "message_id": msg.get("Message-ID"),
                    "in_reply_to": msg.get("In-Reply-To"),
                    "references": msg.get("References"),
                    "timestamp": msg.get("Date")
                }
                emails.append(payload)

            return emails
    except Exception as e:
        logger.error(f"Error consultando IMAP: {e}")
        return []


def run():
    while True:
        sock = None
        try:
            emails = fetch_unseen_emails()

            if emails:
                sock = connect_to_bus(BUS_HOST, BUS_PORT)
                logger.info("Conectado al bus para enviar lote de correos")

                for email_data in emails:
                    logger.info(f"Enviando correo: {email_data['subject']}")

                    payload_json = json.dumps(email_data, ensure_ascii=True)
                    
                    send_message(sock, SERVICE_TARGET, payload_json)
                    
                    response_bytes = receive_message(sock)

                    if response_bytes:
                        
                        service_bytes = response_bytes[:5]
                        status_bytes = response_bytes[5:7]
                        payload_bytes = response_bytes[7:]

                        service = service_bytes.decode("utf-8", errors="ignore").strip()
                        status = status_bytes.decode("utf-8", errors="ignore").strip()
                        payload = payload_bytes.decode("utf-8", errors="ignore")

                        logger.info(f"Servicio devuelto: {service}")
                        logger.info(f"Status: {status}")
                        logger.info(f"Payload raw: {payload}")

                        try:
                            data = json.loads(payload)
                            logger.info(f"Payload JSON parseado con éxito")
                        except Exception as e:
                            logger.error(f"Error parseando JSON: {e}")
                    else:
                        logger.warning("No se recibió respuesta del bus para este correo.")
                
                sock.close()

        except Exception as e:
            logger.error(f"Error en el bucle del monitor: {e}")
            if sock:
                try: sock.close()
                except: pass

        time.sleep(10)


if __name__ == "__main__":
    run()
import json
import time
import logging
from imapclient import IMAPClient
import email
from email.header import decode_header

from shared.soa_lib import connect_to_bus, send_message, receive_message

# CONFIGURACIÓN
IMAP_HOST = "imap.gmail.com"
EMAIL_ACCOUNT = "natalia.ortega1@mail.udp.cl"
EMAIL_PASSWORD = "wjpn ajyz vhyo xiti"  
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


def extract_body(msg):
    """Extrae cuerpo del correo (soporta multipart)"""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")

    return ""


def fetch_unseen_emails():
    """Obtiene correos no leídos"""
    with IMAPClient(IMAP_HOST) as client:
        client.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        client.select_folder("INBOX")

        messages = client.search(["UNSEEN"])
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
                "timestamp": msg.get("Date")
            }

            emails.append(payload)

        return emails


def run():
    sock = connect_to_bus(BUS_HOST, BUS_PORT)
    logger.info("Conectado al bus")

    while True:
        try:
            emails = fetch_unseen_emails()

            for email_data in emails:
                logger.info(f"Enviando correo: {email_data['subject']}")

                send_message(sock, SERVICE_TARGET, json.dumps(email_data))

                
                response = receive_message(sock)

                if response:
                    decoded = response.decode("utf-8", errors="ignore")

                    service = decoded[:5]
                    status=decoded[5:7]
                    payload = decoded[7:]

                    logger.info(f"Servicio: {service}")
                    logger.info(f"Status: {status}")
                    logger.info(f"Payload raw: {payload}")

                    try:
                        data = json.loads(payload)
                        logger.info(f"Payload JSON: {data}")
                    except Exception as e:
                        logger.error(f"Error parseando JSON: {e}")

            time.sleep(10)

        except Exception as e:
            logger.error(f"Error en monitor: {e}")
            time.sleep(10)


if __name__ == "__main__":
    run()
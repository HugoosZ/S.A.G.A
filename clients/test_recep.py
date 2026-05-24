import json
from shared.soa_lib import connect_to_bus, send_message, receive_message

sock = connect_to_bus()

payload = {
    "sender": "usuario<jp@udp.cl>",
    "subject": "Re: asunto del correo",
    "body": "cuerpo del correo",
    "message_id": "<msg123>",
    "in_reply_to": None,
    "timestamp": "2026-05-23T12:00:00"
}

# Enviar a service/recep
send_message(sock, "recep", json.dumps(payload))

# Esperar respuesta
response = receive_message(sock)

print("Respuesta del servicio:")
print(response.decode())
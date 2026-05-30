import json
from shared.soa_lib import connect_to_bus, send_message, receive_message

print("Conectando al BUS...")
sock = connect_to_bus()

payload = {"file_path": "./files/practicas-guia-1-ICIT.pdf"}
payload_str = json.dumps(payload)
print("Enviando payload:", payload_str)
send_message(sock, "docum", payload_str)

resp = receive_message(sock)
if resp is None:
    print("No se recibió respuesta.")
else:
    # respuesta viene con prefijo del servicio (5 bytes en tu protocolo)
    try:
        decoded = resp[5:].decode('utf-8', errors='ignore')
    except Exception:
        decoded = repr(resp)
    print("Respuesta cruda:", resp)
    print("Respuesta decodificada (sin prefijo):", decoded)

sock.close()
print("Client finished.")
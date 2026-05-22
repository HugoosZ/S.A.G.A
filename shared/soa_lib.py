import os
import socket

def connect_to_bus(host: str | None = None, port: int | None = None):
    host = host or os.getenv("BUS_HOST", "localhost")
    port = int(port or os.getenv("BUS_PORT", "5001"))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Conectando a {host} en puerto {port}...")
    sock.connect((host, port)) 
    return sock

def send_message(sock, service_name, payload):
    # concatenar el nombre del servicio y el payload 
    content = service_name.encode() + payload.encode()
    length = str(len(content)).zfill(5)
    message = length.encode() + content
    sock.sendall(message)

def receive_message(sock):
    raw_len = sock.recv(5)
    if not raw_len: 
        return None
    try:
        amount_expected = int(raw_len)
    except ValueError:
        return None
        
    data = b''
    while len(data) < amount_expected:
        chunk = sock.recv(amount_expected - len(data))
        if not chunk: break
        data += chunk
    return data

import socket
import threading

# nombre_servicio -> socket_del_servicio
servicios_registrados = {}

# nombre_servicio -> socket_del_cliente_esperando
clientes_pendientes = {}


def handle_client(conn, addr):
    print(f"[+] Conexión aceptada desde {addr}")
    try:
        while True:
            raw_len = conn.recv(5)
            if not raw_len:
                break
            try:
                amount_expected = int(raw_len)
            except ValueError:
                break

            data = b''
            while len(data) < amount_expected:
                chunk = conn.recv(amount_expected - len(data))
                if not chunk:
                    break
                data += chunk

            if len(data) < 5:
                continue

            # primeros 5 bytes definen la etiqueta de enrutamiento
            comando_o_servicio = data[:5].decode('utf-8', errors='ignore')
            payload = data[5:]

            if comando_o_servicio == "sinit":
                # servicio presentándose al bus
                nombre_servicio = payload.decode('utf-8', errors='ignore')[:5]
                servicios_registrados[nombre_servicio] = conn
                print(
                    f"[SAGA-BUS] Servicio '{nombre_servicio}' registrado exitosamente.")

                # confirmación al servicio
                respuesta = b"bus  OK"
                longitud = str(len(respuesta)).zfill(5).encode()
                conn.sendall(longitud + respuesta)

            else:
                servicio_destino = comando_o_servicio
                longitud = str(len(data)).zfill(5).encode()

                if conn in servicios_registrados.values():
                    # mensaje viene de un servicio como respuesta, por lo que se enruta de vuelta al cliente que lo solicitó.
                    if servicio_destino in clientes_pendientes:
                        socket_cliente = clientes_pendientes[servicio_destino]
                        try:
                            socket_cliente.sendall(longitud + data)
                            print(
                                f"[SAGA-BUS] Respuesta de '{servicio_destino}' entregada al cliente.")
                            del clientes_pendientes[servicio_destino]
                        except Exception as e:
                            print(
                                f"[-] Error enviando respuesta al cliente: {e}")
                    else:
                        print(
                            f"[!] El servicio '{servicio_destino}' respondió, pero el cliente ya no está.")

                else:
                    # mensaje viene de un cliente, es una petición, por lo que se debe enrutar al servicio correspondiente.
                    if servicio_destino in servicios_registrados:
                        socket_destino = servicios_registrados[servicio_destino]

                        # guarda en memoria qué cliente está esperando a este servicio
                        clientes_pendientes[servicio_destino] = conn

                        try:
                            socket_destino.sendall(longitud + data)
                            print(
                                f"[SAGA-BUS] Petición de cliente enrutada al servicio '{servicio_destino}'.")
                        except Exception as e:
                            print(
                                f"[-] Error enviando petición a '{servicio_destino}': {e}")
                            del servicios_registrados[servicio_destino]
                    else:
                        print(
                            f"[!] Cliente solicitó '{servicio_destino}', pero no está en línea.")

    except Exception as e:
        print(f"[-] Excepción en conexión {addr}: {e}")
    finally:
        servicios_caidos = [
            k for k, v in servicios_registrados.items() if v == conn]
        for s in servicios_caidos:
            del servicios_registrados[s]
            print(f"[SAGA-BUS] Servicio '{s}' dado de baja por desconexión.")
        conn.close()
        print(f"[-] Desconexión de {addr}")


def start_bus(host='localhost', port=5000):
    print("[INICIANDO] Bus SOA SAGA...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    print(f"[ESCUCHANDO] Bus activo en {host}:{port} esperando componentes...")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
    except KeyboardInterrupt:
        print("\n[APAGANDO] Bus SOA detenido por el usuario.")
    finally:
        server.close()


if __name__ == "__main__":
    start_bus()

# TAXONOMÍA DE SERVICIOS EN SAGA (ASÍ SE DEBERÍAN LLAMAR LOS SERVICIOS):
# recep: Servicio de Gestión de Recepción de Correos.
# class: Servicio de clasificación con LLM.
# ragsv: Servicio de Generación Aumentada por Recuperación (RAG).
# casos: Servicio de Gestión de Casos.
# docum: Servicio de Gestión de Documentos.
# metri: Servicio de Métricas y Auditoría.

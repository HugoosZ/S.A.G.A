import os
import json
import time
from shared.soa_lib import connect_to_bus, send_message, receive_message

def ingest_all_pdfs(directory="./files"):
    if not os.path.exists(directory):
        print(f"Directorio no encontrado: {directory}")
        return

    pdf_files = [f for f in os.listdir(directory) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"No se encontraron archivos PDF en {directory}")
        return
        
    print(f"Se encontraron {len(pdf_files)} archivos PDF para ingestar.")
    
    # Nos conectamos al bus una sola vez y lo mantenemos abierto
    # O conectamos por cada archivo para evitar timeouts. Mejor por archivo.
    
    for idx, filename in enumerate(pdf_files, 1):
        file_path = os.path.join(directory, filename)
        print(f"\n[{idx}/{len(pdf_files)}] Iniciando ingesta de: {filename}")
        
        sock = connect_to_bus()
        payload = {"file_path": file_path}
        payload_str = json.dumps(payload)
        
        send_message(sock, "docum", payload_str)
        
        # Esperar la respuesta (esto se bloquea hasta que docum termine de procesar el archivo)
        resp = receive_message(sock)
        if resp is None:
            print(f"No se recibió respuesta para {filename}.")
        else:
            try:
                # El prefijo es "documOK", que son 7 caracteres.
                decoded = resp[7:].decode('utf-8', errors='ignore')
                parsed = json.loads(decoded)
                if parsed.get("status") == "success":
                    print(f"Éxito: {parsed.get('chunks_agregados')} fragmentos procesados.")
                else:
                    print(f"Error reportado: {parsed.get('message', decoded)}")
            except Exception:
                print(f"Respuesta no parseable: {resp}")
        
        sock.close()
        
        # Pequeña pausa entre documentos por sanidad
        time.sleep(2)

    print("\n¡Ingesta masiva completada!")

if __name__ == "__main__":
    print("Iniciando proceso de ingesta masiva...")
    ingest_all_pdfs()

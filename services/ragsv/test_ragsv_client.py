import sys
import os
import json

# Forzar rutas para usar la librería compartida
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from shared.soa_lib import connect_to_bus, send_message, receive_message

def test_ragsv():
    print("Conectando al BUS...")
    sock = connect_to_bus()
    
    if sock is None:
        print("Error: No se pudo conectar al BUS.")
        return

    # La pregunta que enviaremos a Gemini
    payload = {
        "question": "¿De qué trata el Proyecto de Arquitectura de Software? Explica brevemente."
    }
    
    payload_str = json.dumps(payload)
    print(f"Enviando payload a ragsv: {payload_str}")
    
    # Enviar mensaje al servicio "ragsv"
    send_message(sock, "ragsv", payload_str)
    
    # Esperar respuesta
    resp = receive_message(sock)
    if resp is None:
        print("No se recibió respuesta (Timeout o error).")
    else:
        # Imprimir respuesta cruda para debug
        print(f"Respuesta cruda: {resp}")
        
        # Parsear la respuesta
        try:
            # El bus devuelve el prefijo (ej: b'ragsvOK{"status"...}')
            decoded_str = resp.decode('utf-8', errors='ignore')
            
            # Buscamos dónde empieza realmente el JSON
            json_start = decoded_str.find('{')
            if json_start != -1:
                clean_json = decoded_str[json_start:]
                parsed = json.loads(clean_json)
                print("\n" + "="*50)
                print("RESPUESTA DE GEMINI:")
                print("="*50)
                print(parsed.get("answer", "No hay campo 'answer'"))
                print("\n[Métricas de Uso]")
                print(f"- Tokens gastados: {parsed.get('tokens_used')}")
                print(f"- Tipo de query: {parsed.get('query_type')}")
                print("="*50)
            else:
                print(f"\nRespuesta decodificada (sin JSON): {decoded_str}")
        except Exception as e:
            print(f"Error al procesar la respuesta: {e}")
            print(f"Data: {resp}")

    sock.close()
    print("Client finished.")

if __name__ == "__main__":
    test_ragsv()
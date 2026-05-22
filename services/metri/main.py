import os
from shared.service_base import start_service

def procesar_metrica(datos_peticion: dict) -> dict:
    """
    Función pura de negocio: Recibe el diccionario validado desde el Bus, 
    procesa la métrica en la base de datos y retorna la respuesta estándar.
    """
    print(f"Datos de métrica recibidos: {datos_peticion}")
    
    try:
        # meter lógica base de datos
        
        # El diccionario retornado se convierte automáticamente en JSON por la plantilla
        return {
            "status": "ok",
            "mensaje": "Métrica almacenada correctamente en PostgreSQL"
        }
    except Exception as e:
        return {
            "status": "error",
            "mensaje": f"Falla interna: {str(e)}"
        }

if __name__ == "__main__":
    
    NOMBRE_SERVICIO = "metri"
    
    print(f"Inicializando Servicio de Métricas ({NOMBRE_SERVICIO})...")
    
    start_service(NOMBRE_SERVICIO, procesar_metrica)
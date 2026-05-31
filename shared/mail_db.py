import psycopg2
import os

def get_connection():
    # Se capturan las variables inyectadas por el docker-compose
    # Si no existen, utiliza valores por defecto
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_name = os.getenv("POSTGRES_DB", "saga_db")
    db_user = os.getenv("POSTGRES_USER", "saga_user")
    db_pass = os.getenv("POSTGRES_PASSWORD", "saga_pass")
    db_port = os.getenv("POSTGRES_PORT", "5432")

    return psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_pass,
        port=db_port
    )

def init_db():
    """Inicializa las tablas necesarias si no existen."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Se crea la tabla de correos según el modelo de datos (RF04/RF18)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                message_id VARCHAR(255) PRIMARY KEY,
                thread_id VARCHAR(255),
                in_reply_to VARCHAR(255),
                sender VARCHAR(255),
                subject TEXT,
                body TEXT,
                timestamp TIMESTAMP,
                is_reply BOOLEAN
            );
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inicializando la base de datos: {e}")
        raise e
    finally:
        cur.close()
        conn.close()
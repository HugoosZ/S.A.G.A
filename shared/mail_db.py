import psycopg2
import os

# Se modifico por error de conexión en la red
def get_connection():
    # Se capturan las variables inyectadas por Docker
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
    """
    Crea la tabla de emails e índices automáticamente si no existen en la DB.
    """
    
    conn = get_connection()
    cur = conn.cursor()
    
    table_query = """
    CREATE TABLE IF NOT EXISTS emails (
        id SERIAL PRIMARY KEY,
        message_id TEXT UNIQUE NOT NULL,
        thread_id TEXT NOT NULL,
        in_reply_to TEXT,
        sender TEXT,
        subject TEXT,
        body TEXT,
        timestamp TEXT,
        is_reply BOOLEAN DEFAULT FALSE
    );
    CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
    CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);
    """
    try:
        cur.execute(table_query)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inicializando las tablas: {e}")
    finally:
        cur.close()
        conn.close()
import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="saga_db",
        user="saga_user",
        password="saga_pass",
        host="localhost",
        port="5432"
    )

def init_db():
    """
    Crea la tabla de emails e índices automáticamente si no existen en la DB.
    """
    from shared.mail_db import get_connection
    
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
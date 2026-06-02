from shared.mail_db import get_connection
import datetime

def registrar_intento_historial(correo_usuario: str, thread_id: str):
    'Guarda el registro en un historial de consultas'
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO historial_consultas(correo_usuario, thread_id, fecha, resuelto)
            VALUES (%s, %s, CURRENT_TIMESTAMP, FALSE)
        """, (correo_usuario, thread_id))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar intento en historial: {e}")
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def calcular_prioridad_dinámica(correo_usuario: str) -> tuple:
    'Calcula la prioridad de un caso basado en el historial del usuario en los últimos 30 días'
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) FROM historial_consultas
            WHERE correo_usuario = %s AND resuelto = FALSE
        """, (correo_usuario,))
        intentos_pendientes = cur.fetchone()[0]
        
        #Lógica de asignación de prioridad basada en RF12

        if intentos_pendientes <=1:
            return "Baja", intentos_pendientes
        elif intentos_pendientes ==2:
            return "Media", intentos_pendientes
        elif intentos_pendientes ==3:
            return "Alta", intentos_pendientes
        else:
            return "Crítica", intentos_pendientes
    finally:
        cur.close()
        conn.close()

def derivar_a_secretaría(thread_id: str, correo_usuario: str, motivo: str) -> dict:
    'Deriva el caso a la Secretaría General con la prioridad calculada'
    registrar_intento_historial(correo_usuario, thread_id)
    prioridad, intentos_pendientes = calcular_prioridad_dinámica(correo_usuario)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO casos (thread_id, estado, prioridad, asignado_a, num_intentos, motivo_derivacion, fecha_actualizacion)
            VALUES (%s, 'derivado', %s, 'secretaria', %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (thread_id) DO UPDATE SET
                estado = 'derivado',
                prioridad = %s,
                num_intentos = casos.num_intentos + 1,
                motivo_derivacion = %s,
                fecha_actualizacion = CURRENT_TIMESTAMP
            RETURNING thread_id, estado, prioridad, num_intentos;
        """, (thread_id, prioridad, intentos_pendientes, motivo, prioridad, motivo))
        
        row = cur.fetchone()
        conn.commit()
        return {
            "thread_id": row[0],
            "estado": row[1],
            "prioridad": row[2],
            "intentos_detectados": row[3],
            "asignado_a": "secretaria"
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def cambiar_estado_caso(thread_id: str, nuevo_estado: str, motivo: str = None) -> bool:
    'Cambia el estado de un caso y registra el motivo'
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE casos
            SET estado = %s, motivo_derivacion = %s, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE thread_id = %s
        """, (nuevo_estado, motivo, thread_id))

        if nuevo_estado in ['resulto_auto', 'resuelto_manual']:
            cur.execute("""
                UPDATE historial_consultas
                SET resuelto = TRUE
                WHERE thread_id = %s
            """, (thread_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def init_casos_db():
    """
    Crea las tablas 'casos' e 'historial_consultas' de forma automática 
    si no existen en la base de datos de PostgreSQL.
    """
    from shared.mail_db import get_connection
    
    conn = get_connection()
    cur = conn.cursor()
    
    sql_script = """
    CREATE TABLE IF NOT EXISTS casos (
        id SERIAL PRIMARY KEY,
        thread_id TEXT UNIQUE NOT NULL,
        estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
        prioridad VARCHAR(20) NOT NULL DEFAULT 'Baja',
        asignado_a VARCHAR(50) NOT NULL DEFAULT 'sistema_ia',
        num_intentos INTEGER DEFAULT 1,
        motivo_derivacion TEXT,
        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS historial_consultas (
        id_historial SERIAL PRIMARY KEY,
        correo_usuario VARCHAR(255) NOT NULL,
        thread_id TEXT NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resuelto BOOLEAN DEFAULT FALSE
    );

    CREATE INDEX IF NOT EXISTS idx_casos_thread_id ON casos(thread_id);
    CREATE INDEX IF NOT EXISTS idx_historial_correo ON historial_consultas(correo_usuario);
    """
    try:
        cur.execute(sql_script)
        conn.commit()
        print("[DATABASE] Tablas del módulo CASOS verificadas/creadas con éxito.")
    except Exception as e:
        conn.rollback()
        print(f"[DATABASE] Error al inicializar tablas de CASOS: {e}")
    finally:
        cur.close()
        conn.close()
import os
import psycopg2


def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("SAGA_DB_NAME", "saga_db"),
        user=os.getenv("SAGA_DB_USER", "saga_user"),
        password=os.getenv("SAGA_DB_PASSWORD", "saga_pass"),
        host=os.getenv("SAGA_DB_HOST", "localhost"),
        port=os.getenv("SAGA_DB_PORT", "5432"),
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


def init_documentos_db():
    """
    Crea la tabla de documentos institucionales que alimentan al motor RAG.
    Es la fuente de verdad para el portal administrativo.
    """
    conn = get_connection()
    cur = conn.cursor()

    table_query = """
    CREATE TABLE IF NOT EXISTS documentos (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL UNIQUE,
        tipo TEXT NOT NULL,
        fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tamano_kb INTEGER DEFAULT 0,
        paginas INTEGER DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'activo',
        cargado_por TEXT DEFAULT 'Secretaría FIC',
        chunks_indexados INTEGER DEFAULT 0,
        ruta_archivo TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_documentos_estado ON documentos(estado);
    CREATE INDEX IF NOT EXISTS idx_documentos_tipo ON documentos(tipo);
    """
    try:
        cur.execute(table_query)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inicializando la tabla documentos: {e}")
    finally:
        cur.close()
        conn.close()


# ── DAO: documentos ─────────────────────────────────────────────────────────

_DOC_COLS = (
    "id, nombre, tipo, fecha_carga, tamano_kb, paginas, "
    "estado, cargado_por, chunks_indexados, ruta_archivo"
)


def _row_to_documento(row):
    return {
        "id": row[0],
        "nombre": row[1],
        "tipo": row[2],
        "fecha_carga": row[3],
        "tamano_kb": row[4] or 0,
        "paginas": row[5] or 0,
        "estado": row[6],
        "cargado_por": row[7] or "Secretaría FIC",
        "chunks_indexados": row[8] or 0,
        "ruta_archivo": row[9],
    }


def upsert_documento(
    nombre: str,
    tipo: str,
    tamano_kb: int,
    paginas: int = 0,
    chunks_indexados: int = 0,
    ruta_archivo: str | None = None,
    cargado_por: str = "Secretaría FIC",
) -> dict:
    """
    Inserta o actualiza un documento por nombre. Si ya existe, se refresca
    fecha_carga, tamano, páginas y chunks indexados.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            INSERT INTO documentos (
                nombre, tipo, tamano_kb, paginas,
                chunks_indexados, ruta_archivo, cargado_por
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (nombre) DO UPDATE SET
                tipo = EXCLUDED.tipo,
                tamano_kb = EXCLUDED.tamano_kb,
                paginas = EXCLUDED.paginas,
                chunks_indexados = EXCLUDED.chunks_indexados,
                ruta_archivo = EXCLUDED.ruta_archivo,
                fecha_carga = CURRENT_TIMESTAMP,
                estado = 'activo'
            RETURNING {_DOC_COLS};
            """,
            (nombre, tipo, tamano_kb, paginas, chunks_indexados, ruta_archivo, cargado_por),
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_documento(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def list_documentos(filtro_estado: str = "todos", filtro_tipo: str = "todos") -> list:
    conn = get_connection()
    cur = conn.cursor()
    try:
        where = []
        params = []
        if filtro_estado != "todos":
            where.append("estado = %s")
            params.append(filtro_estado)
        if filtro_tipo != "todos":
            where.append("tipo = %s")
            params.append(filtro_tipo)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        cur.execute(
            f"SELECT {_DOC_COLS} FROM documentos {clause} ORDER BY fecha_carga DESC;",
            params,
        )
        return [_row_to_documento(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def toggle_documento(doc_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            UPDATE documentos
            SET estado = CASE WHEN estado = 'activo' THEN 'inactivo' ELSE 'activo' END
            WHERE id = %s
            RETURNING {_DOC_COLS};
            """,
            (doc_id,),
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_documento(row) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def delete_documento(doc_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"DELETE FROM documentos WHERE id = %s RETURNING {_DOC_COLS};",
            (doc_id,),
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_documento(row) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def count_documentos_by_tipo() -> dict:
    """Devuelve {tipo: cantidad} sólo de documentos activos."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT tipo, COUNT(*) FROM documentos
            WHERE estado = 'activo'
            GROUP BY tipo
            ORDER BY COUNT(*) DESC;
            """
        )
        return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        cur.close()
        conn.close()


# ── DAO: emails / casos (lectura para el dashboard) ─────────────────────────

def list_recent_emails(limit: int = 10) -> list:
    """
    Devuelve los correos más recientes con su estado derivado del módulo casos.
    Si la tabla casos aún no existe (servicio casos no se ha levantado), se
    asume 'recibido' como estado y se omite la unión.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT to_regclass('public.casos') IS NOT NULL;
            """
        )
        has_casos = cur.fetchone()[0]

        if has_casos:
            cur.execute(
                """
                SELECT
                    e.id, e.subject, e.sender, e.timestamp, e.thread_id,
                    c.estado, c.prioridad
                FROM emails e
                LEFT JOIN casos c ON c.thread_id = e.thread_id
                ORDER BY e.id DESC
                LIMIT %s;
                """,
                (limit,),
            )
        else:
            cur.execute(
                """
                SELECT
                    e.id, e.subject, e.sender, e.timestamp, e.thread_id,
                    NULL::text, NULL::text
                FROM emails e
                ORDER BY e.id DESC
                LIMIT %s;
                """,
                (limit,),
            )

        rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "asunto": row[1] or "(sin asunto)",
                "remitente": row[2] or "(desconocido)",
                "fecha": row[3],
                "thread_id": row[4],
                "estado_caso": row[5],   # 'derivado' | 'resuelto_*' | None
                "prioridad": row[6],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()


def count_emails_by_estado_caso() -> dict:
    """
    Cuenta correos agrupando por estado del caso (derivado vs auto-procesado).
    Útil como fallback cuando no hay clasificación por categoría.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT to_regclass('public.casos') IS NOT NULL;")
        has_casos = cur.fetchone()[0]
        if not has_casos:
            cur.execute("SELECT COUNT(*) FROM emails;")
            total = cur.fetchone()[0] or 0
            return {"PROCESADO": total} if total else {}

        cur.execute(
            """
            SELECT
                COALESCE(c.estado, 'auto') AS estado,
                COUNT(*) AS cantidad
            FROM emails e
            LEFT JOIN casos c ON c.thread_id = e.thread_id
            GROUP BY COALESCE(c.estado, 'auto')
            ORDER BY cantidad DESC;
            """
        )
        return {row[0].upper(): row[1] for row in cur.fetchall()}
    finally:
        cur.close()
        conn.close()

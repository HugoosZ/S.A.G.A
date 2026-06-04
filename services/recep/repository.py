from shared.mail_db import get_connection
from utils import clean_reply_history

def get_thread_messages(thread_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT sender, subject, body, timestamp
        FROM emails
        WHERE thread_id = %s
        ORDER BY timestamp ASC
    """, (thread_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def get_email_by_message_id(message_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT message_id, thread_id
        FROM emails
        WHERE message_id = %s
        """,
        (message_id,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "message_id": row[0],
        "thread_id": row[1]
    }

def build_conversation(thread_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT sender, subject, body, timestamp
        FROM emails
        WHERE thread_id = %s
        ORDER BY timestamp ASC
    """, (thread_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    messages = []

    for row in rows:
        body_clean = clean_reply_history(row[2])

        messages.append({
            "sender": row[0],
            "subject": row[1],
            "body": body_clean,
            "timestamp": row[3]
        })

    return {
        "thread_id": thread_id,
        "messages": messages
    }



def save_email(data: dict):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # resolver hilo REAL usando DB
        thread_id = resolve_thread_id(data)

        cur.execute(
            """
            INSERT INTO emails (
                message_id,
                thread_id,
                in_reply_to,
                sender,
                subject,
                body,
                timestamp,
                is_reply
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING;
            """,
            (
                data.get("message_id"),
                thread_id,  # 👈 AQUÍ EL CAMBIO
                data.get("in_reply_to"),
                data.get("sender"),
                data.get("subject"),
                data.get("body"),
                data.get("timestamp"),
                data.get("is_reply"),
            )
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()

def resolve_thread_id(data: dict):
    in_reply_to = data.get("in_reply_to")

    if not in_reply_to:
        return data["hilo_id"]

    parent = get_email_by_message_id(in_reply_to)

    if parent:
        return parent["thread_id"]

    return data["hilo_id"]
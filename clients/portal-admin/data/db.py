"""
Capa de datos del portal administrativo.

Hace de fachada sobre los backends reales del sistema SAGA:
- Postgres (`shared.mail_db`) para documentos institucionales y correos.
- Prometheus (`data.metrics`) para KPIs y series temporales.
- BUS (`data.bus_client`) para disparar la ingestión de PDFs hacia `docum`.

Las vistas (`dashboard_view`, `documentos_view`) sólo conocen esta capa.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from shared import mail_db

from data import metrics
from data.bus_client import (
    IngestionError,
    count_pdf_pages,
    ingest_pdf_via_bus,
    stage_pdf,
)


# Tipos válidos de documentos (compartidos por la UI). Estos son los rótulos
# que el usuario elige en la dropzone; cualquier valor extra cae en "otro".
TIPOS_DOCUMENTO = {
    "reglamento":  "Reglamento",
    "malla":       "Malla Curricular",
    "calendario":  "Calendario Académico",
    "faq":         "Preguntas Frecuentes",
    "tramite":     "Procedimiento / Trámite",
    "otro":        "Otro",
}


# ── Inicialización ─────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Verifica/crea las tablas que necesita el portal. Es idempotente.
    Si Postgres no está corriendo, captura la excepción y permite que la UI
    abra igualmente — las vistas mostrarán estados vacíos.
    """
    try:
        mail_db.init_db()
        mail_db.init_documentos_db()
    except Exception as e:  # noqa: BLE001
        print(f"[portal] No se pudo inicializar Postgres: {e}")


# ── Documentos ─────────────────────────────────────────────────────────────

def get_documentos(filtro_estado: str = "todos", filtro_tipo: str = "todos") -> list[dict[str, Any]]:
    try:
        return mail_db.list_documentos(filtro_estado, filtro_tipo)
    except Exception as e:  # noqa: BLE001
        print(f"[portal] Error consultando documentos: {e}")
        return []


def ingest_documento(source_path, tipo: str) -> dict[str, Any]:
    """
    Flujo completo de carga:
    1. Copia el PDF al directorio `resources/` del monorepo.
    2. Pide al servicio `docum` que lo ingese (chunks + embeddings + tripletas KG).
    3. Persiste la ficha en Postgres si la ingestión fue exitosa.

    Lanza IngestionError ante fallos recuperables (BUS caído, PDF inválido).
    """
    from pathlib import Path

    src = Path(source_path)
    if not src.exists():
        raise IngestionError(f"El archivo {src} no existe.")
    if tipo not in TIPOS_DOCUMENTO:
        tipo = "otro"

    staged = stage_pdf(src)
    paginas = count_pdf_pages(staged)
    tamano_kb = max(1, staged.stat().st_size // 1024)

    response = ingest_pdf_via_bus(staged)
    if response.get("status") != "success":
        raise IngestionError(response.get("message") or "Ingestión fallida en docum.")

    chunks = int(response.get("chunks_agregados") or 0)
    doc = mail_db.upsert_documento(
        nombre=staged.name,
        tipo=tipo,
        tamano_kb=tamano_kb,
        paginas=paginas,
        chunks_indexados=chunks,
        ruta_archivo=str(staged),
    )
    return doc


def toggle_documento(doc_id: int):
    try:
        return mail_db.toggle_documento(doc_id)
    except Exception as e:  # noqa: BLE001
        print(f"[portal] Error toggling doc {doc_id}: {e}")
        return None


def delete_documento(doc_id: int):
    try:
        return mail_db.delete_documento(doc_id)
    except Exception as e:  # noqa: BLE001
        print(f"[portal] Error eliminando doc {doc_id}: {e}")
        return None


# ── Métricas (Prometheus + Postgres) ───────────────────────────────────────

def get_metricas_resumen() -> dict[str, Any]:
    resumen = metrics.get_resumen()
    # KPI extra: cantidad de documentos en la base de conocimiento.
    try:
        activos = mail_db.list_documentos(filtro_estado="activo")
        todos = mail_db.list_documentos()
        resumen["documentos_activos"] = len(activos)
        resumen["documentos_total"] = len(todos)
    except Exception:  # noqa: BLE001
        resumen["documentos_activos"] = 0
        resumen["documentos_total"] = 0
    return resumen


def get_serie_historica() -> list[dict[str, Any]]:
    return metrics.get_serie_historica(dias=30)


def get_clasificaciones() -> dict[str, int]:
    """
    El clasificador semántico aún no persiste categorías en Postgres ni emite
    métricas a Prometheus, así que el donut del dashboard muestra la
    composición de la base de conocimiento (documentos activos por tipo),
    que es la información real que el portal sí maneja.
    """
    try:
        crudo = mail_db.count_documentos_by_tipo()
    except Exception:  # noqa: BLE001
        return {}
    return {TIPOS_DOCUMENTO.get(k, k.upper()): v for k, v in crudo.items()}


def _coerce_email_timestamp(value) -> datetime:
    """
    El monitor_agente persiste el header `Date` crudo del correo (RFC 5322), pero
    si recep es actualizado podría llegar también en ISO. Aceptamos ambos y
    caemos a `now()` ante cualquier error para no romper la UI.
    """
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now()
    text = str(value)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        if parsed is None:
            return datetime.now()
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except (TypeError, ValueError):
        return datetime.now()


def get_correos_recientes(limit: int = 10) -> list[dict[str, Any]]:
    try:
        rows = mail_db.list_recent_emails(limit=limit)
    except Exception as e:  # noqa: BLE001
        print(f"[portal] Error consultando correos: {e}")
        return []

    salida = []
    for r in rows:
        estado_caso = r.get("estado_caso")
        if estado_caso == "derivado":
            estado = "derivado"
        else:
            estado = "respondido_auto"

        clasificacion = "SIN CLASIF."
        if r.get("prioridad"):
            clasificacion = str(r["prioridad"]).upper()

        fecha = _coerce_email_timestamp(r.get("fecha"))

        salida.append({
            "id": r["id"],
            "asunto": r["asunto"],
            "remitente": r["remitente"],
            "fecha": fecha,
            "clasificacion": clasificacion,
            "estado": estado,
            "confianza": None,  # el sistema aún no expone confianza del clasificador
        })
    return salida

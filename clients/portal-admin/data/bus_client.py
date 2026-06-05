"""
Cliente del BUS (ESB) para el portal administrativo.

Encargado de despachar peticiones de ingestión al servicio `docum`, que es
quien finalmente actualiza ChromaDB (vectores) y el Knowledge Graph (tripletas
RDF) a través de packages.rag_core.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
from pathlib import Path


# Por defecto el portal corre en el host, así que apunta a los puertos publicados
# por docker-compose. Variables de entorno permiten redirigir en producción.
BUS_HOST = os.getenv("SAGA_BUS_HOST", "localhost")
BUS_PORT = int(os.getenv("SAGA_BUS_PORT", "5001"))
INGEST_TIMEOUT_S = float(os.getenv("SAGA_INGEST_TIMEOUT_S", "600"))

# Ubicación del directorio `resources/` del monorepo, que está bind-mounted como
# /app/files dentro del contenedor `saga-service-docum`.
_THIS_FILE = Path(__file__).resolve()
REPO_ROOT = Path(os.getenv("SAGA_REPO_ROOT") or _THIS_FILE.parents[3])
RESOURCES_DIR = Path(os.getenv("SAGA_RESOURCES_DIR") or (REPO_ROOT / "resources"))


# ── Protocolo SOA (formato compartido con shared/soa_lib.py) ───────────────

def _send(sock: socket.socket, service_name: str, payload: str) -> None:
    if len(service_name) != 5:
        raise ValueError("El nombre del servicio debe tener 5 caracteres exactos.")
    content = service_name.encode() + payload.encode()
    length = str(len(content)).zfill(5)
    sock.sendall(length.encode() + content)


def _recv(sock: socket.socket) -> bytes:
    raw_len = sock.recv(5)
    if not raw_len:
        return b""
    try:
        expected = int(raw_len)
    except ValueError:
        return b""
    data = b""
    while len(data) < expected:
        chunk = sock.recv(expected - len(data))
        if not chunk:
            break
        data += chunk
    return data


def _parse_response(raw: bytes) -> dict:
    """
    El BUS antepone al payload el nombre del servicio (5 chars) y, según versión,
    también un sufijo de status (`OK`/`NK`). Por robustez buscamos el primer
    `{` para arrancar el JSON.
    """
    if not raw:
        return {"status": "error", "message": "El BUS no devolvió respuesta."}
    text = raw.decode("utf-8", errors="ignore")
    idx = text.find("{")
    if idx < 0:
        return {"status": "error", "message": f"Respuesta no parseable: {text!r}"}
    try:
        return json.loads(text[idx:])
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"JSON inválido en respuesta: {e}"}


# ── API pública ────────────────────────────────────────────────────────────

class IngestionError(Exception):
    pass


def stage_pdf(source: Path) -> Path:
    """
    Copia el PDF al directorio `resources/` del monorepo (montado en el
    contenedor `docum`). Si ya está allí, devuelve la ruta tal cual.
    Devuelve la ruta absoluta del archivo destino.
    """
    if source.suffix.lower() != ".pdf":
        raise IngestionError(
            f"El motor RAG sólo indexa archivos PDF (recibido: {source.suffix})."
        )

    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    dest = RESOURCES_DIR / source.name
    if dest.resolve() != source.resolve():
        shutil.copy2(source, dest)
    return dest


def ingest_pdf_via_bus(staged_path: Path) -> dict:
    """
    Envía al servicio `docum` la ruta relativa esperada dentro del contenedor
    (`./files/<nombre>.pdf`). Bloquea hasta recibir la respuesta del servicio
    (chunking + embeddings + extracción de tripletas si GRAPH_EXTRACT_ON_INGEST=true).
    """
    if not staged_path.exists():
        raise IngestionError(f"Archivo no encontrado tras copiar: {staged_path}")

    # docum/main.py resuelve la ruta contra ROOT_DIR=/app y exige que esté bajo /app/files
    container_path = f"./files/{staged_path.name}"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(INGEST_TIMEOUT_S)
    try:
        sock.connect((BUS_HOST, BUS_PORT))
        _send(sock, "docum", json.dumps({"file_path": container_path}))
        raw = _recv(sock)
    except (socket.timeout, ConnectionError, OSError) as e:
        raise IngestionError(
            f"No se pudo comunicar con el BUS ({BUS_HOST}:{BUS_PORT}): {e}"
        ) from e
    finally:
        try:
            sock.close()
        except OSError:
            pass

    return _parse_response(raw)


def count_pdf_pages(path: Path) -> int:
    """
    Cuenta páginas con PyPDF2 si está disponible; si no, devuelve 0 silenciosamente.
    No es crítico para la ingestión: es un dato cosmético del catálogo.
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return 0
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return 0

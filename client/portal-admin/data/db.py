"""
Base de datos en memoria con datos de ejemplo para la demostración.
En producción, esto se reemplaza por conexiones SQL al PostgreSQL del proyecto.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random

# ── "Tablas" en memoria ─────────────────────────────────────────────────────
documentos: List[Dict[str, Any]] = []
metricas_diarias: List[Dict[str, Any]] = []
clasificaciones: Dict[str, int] = {}
correos_recientes: List[Dict[str, Any]] = []


def init_db() -> None:
    """Inicializa la base de datos con datos de muestra."""
    _cargar_documentos_ejemplo()
    _generar_metricas_historicas()
    _generar_clasificaciones()
    _generar_correos_recientes()


def _cargar_documentos_ejemplo() -> None:
    global documentos
    documentos = [
        {
            "id": 1,
            "nombre": "Reglamento de Pregrado UDP 2026.pdf",
            "tipo": "reglamento",
            "fecha_carga": datetime(2026, 3, 12, 10, 30),
            "tamano_kb": 842,
            "estado": "activo",
            "paginas": 47,
            "cargado_por": "Secretaría FIC",
        },
        {
            "id": 2,
            "nombre": "Malla Ingeniería Civil Informática.pdf",
            "tipo": "malla",
            "fecha_carga": datetime(2026, 3, 18, 14, 12),
            "tamano_kb": 312,
            "estado": "activo",
            "paginas": 8,
            "cargado_por": "Secretaría FIC",
        },
        {
            "id": 3,
            "nombre": "Calendario Académico Semestre 1-2026.pdf",
            "tipo": "calendario",
            "fecha_carga": datetime(2026, 3, 5, 9, 0),
            "tamano_kb": 156,
            "estado": "activo",
            "paginas": 3,
            "cargado_por": "Secretaría FIC",
        },
        {
            "id": 4,
            "nombre": "Preguntas Frecuentes - Convalidaciones.pdf",
            "tipo": "faq",
            "fecha_carga": datetime(2026, 4, 1, 11, 45),
            "tamano_kb": 98,
            "estado": "activo",
            "paginas": 4,
            "cargado_por": "Secretaría FIC",
        },
        {
            "id": 5,
            "nombre": "Reglamento de Pregrado UDP 2025.pdf",
            "tipo": "reglamento",
            "fecha_carga": datetime(2025, 8, 20, 16, 30),
            "tamano_kb": 798,
            "estado": "inactivo",
            "paginas": 45,
            "cargado_por": "Secretaría FIC",
        },
        {
            "id": 6,
            "nombre": "Procedimiento Solicitud de Certificados.pdf",
            "tipo": "tramite",
            "fecha_carga": datetime(2026, 4, 8, 13, 20),
            "tamano_kb": 124,
            "estado": "activo",
            "paginas": 2,
            "cargado_por": "Secretaría FIC",
        },
    ]


def _generar_metricas_historicas() -> None:
    """Genera 30 días de métricas con un pico al inicio de semestre."""
    global metricas_diarias
    metricas_diarias = []
    hoy = datetime.now().date()
    for i in range(29, -1, -1):
        fecha = hoy - timedelta(days=i)
        base = 25 + random.randint(-5, 15)
        if i > 20:
            base = 80 + random.randint(-15, 25)
        elif i > 15:
            base = 55 + random.randint(-10, 20)

        respondidos_auto = int(base * random.uniform(0.62, 0.78))
        derivados = base - respondidos_auto
        metricas_diarias.append({
            "fecha": fecha,
            "total": base,
            "respondidos_auto": respondidos_auto,
            "derivados": derivados,
            "tiempo_promedio_s": round(random.uniform(2.1, 4.8), 1),
        })


def _generar_clasificaciones() -> None:
    global clasificaciones
    clasificaciones = {
        "TRAMITE":          187,
        "PLAZO":            142,
        "REGLAMENTO":        98,
        "MALLA":             76,
        "CONVALIDACION":     54,
        "OTRO":              31,
    }


def _generar_correos_recientes() -> None:
    global correos_recientes
    asuntos = [
        ("Consulta sobre certificado de alumno regular",     "TRAMITE",       "respondido_auto"),
        ("¿Cuándo es la fecha de inscripción de ramos?",     "PLAZO",         "respondido_auto"),
        ("Problema con convalidación de Cálculo II",         "CONVALIDACION", "derivado"),
        ("Solicitud cambio de carrera",                       "TRAMITE",       "derivado"),
        ("Horario de atención secretaría",                    "OTRO",          "respondido_auto"),
        ("Requisitos para titulación",                        "REGLAMENTO",    "respondido_auto"),
        ("Malla curricular actualizada",                      "MALLA",         "respondido_auto"),
        ("Reincorporación tras suspensión",                   "REGLAMENTO",    "derivado"),
        ("Inscripción de ramos en periodo extraordinario",    "PLAZO",         "respondido_auto"),
        ("Validación de práctica profesional",                "TRAMITE",       "derivado"),
    ]
    ahora = datetime.now()
    global correos_recientes
    correos_recientes = []
    for i, (asunto, cat, estado) in enumerate(asuntos):
        correos_recientes.append({
            "id": i + 1,
            "asunto": asunto,
            "remitente": f"estudiante{i+1}@mail.udp.cl",
            "fecha": ahora - timedelta(minutes=random.randint(5, 480)),
            "clasificacion": cat,
            "estado": estado,
            "confianza": round(random.uniform(0.72, 0.97), 2),
        })


# ── DAO ─────────────────────────────────────────────────────────────────────
def get_documentos(filtro_estado: str = "todos", filtro_tipo: str = "todos"):
    docs = documentos
    if filtro_estado != "todos":
        docs = [d for d in docs if d["estado"] == filtro_estado]
    if filtro_tipo != "todos":
        docs = [d for d in docs if d["tipo"] == filtro_tipo]
    return sorted(docs, key=lambda d: d["fecha_carga"], reverse=True)


def add_documento(nombre: str, tipo: str, tamano_kb: int, paginas: int = 0):
    nuevo_id = max((d["id"] for d in documentos), default=0) + 1
    doc = {
        "id": nuevo_id,
        "nombre": nombre,
        "tipo": tipo,
        "fecha_carga": datetime.now(),
        "tamano_kb": tamano_kb,
        "estado": "activo",
        "paginas": paginas,
        "cargado_por": "Secretaría FIC",
    }
    documentos.append(doc)
    return doc


def toggle_documento(doc_id: int) -> Optional[Dict[str, Any]]:
    for d in documentos:
        if d["id"] == doc_id:
            d["estado"] = "inactivo" if d["estado"] == "activo" else "activo"
            return d
    return None


def delete_documento(doc_id: int):
    global documentos
    documentos = [d for d in documentos if d["id"] != doc_id]


def get_metricas_resumen():
    ult_7 = metricas_diarias[-7:]
    total_7d = sum(m["total"] for m in ult_7)
    auto_7d = sum(m["respondidos_auto"] for m in ult_7)
    derivados_7d = sum(m["derivados"] for m in ult_7)
    tiempo_prom = sum(m["tiempo_promedio_s"] for m in ult_7) / len(ult_7)

    return {
        "total_7d": total_7d,
        "respondidos_auto_7d": auto_7d,
        "derivados_7d": derivados_7d,
        "tasa_automatizacion": round(auto_7d / total_7d * 100, 1) if total_7d else 0,
        "tiempo_promedio_s": round(tiempo_prom, 1),
        "documentos_activos": len([d for d in documentos if d["estado"] == "activo"]),
        "documentos_total": len(documentos),
    }


def get_serie_historica():
    return metricas_diarias


def get_clasificaciones():
    return clasificaciones


def get_correos_recientes(limit: int = 10):
    return sorted(correos_recientes, key=lambda c: c["fecha"], reverse=True)[:limit]


# Tipos válidos de documentos (compartidos por la UI)
TIPOS_DOCUMENTO = {
    "reglamento":  "Reglamento",
    "malla":       "Malla Curricular",
    "calendario":  "Calendario Académico",
    "faq":         "Preguntas Frecuentes",
    "tramite":     "Procedimiento / Trámite",
    "otro":        "Otro",
}

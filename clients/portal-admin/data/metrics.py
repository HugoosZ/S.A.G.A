"""
Cliente HTTP de Prometheus para el portal administrativo.

Las métricas que consume vienen de:
- saga-service-recep (puerto 8002): recep_processing_latency_seconds_*
- saga-service-ragsv (puerto 8001): llm_processing_latency_seconds_*,
                                    e2e_resolution_latency_seconds_*,
                                    integration_bus_latency_seconds_*

Los jobs de scraping están definidos en prometheus/prometheus.yml.

Cuando Prometheus no está disponible o la métrica aún no existe, las funciones
devuelven valores neutros para que el dashboard pueda renderizar un estado
vacío sin crashear.
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta
from typing import Any

import requests


PROMETHEUS_URL = os.getenv("SAGA_PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("SAGA_GRAFANA_URL", "http://localhost:3000")
HTTP_TIMEOUT_S = float(os.getenv("SAGA_PROMETHEUS_TIMEOUT_S", "3"))


# ── Llamadas crudas a la API de Prometheus ─────────────────────────────────

def _query(promql: str) -> float | None:
    """Devuelve el primer valor escalar de una consulta instantánea."""
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": promql},
            timeout=HTTP_TIMEOUT_S,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return None

    if data.get("status") != "success":
        return None
    result = data.get("data", {}).get("result", [])
    if not result:
        return None
    try:
        return float(result[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _query_range(promql: str, start_ts: float, end_ts: float, step_s: int) -> list[tuple[float, float]]:
    """Devuelve [(timestamp, valor)] de una consulta sobre rango."""
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": promql,
                "start": start_ts,
                "end": end_ts,
                "step": step_s,
            },
            timeout=HTTP_TIMEOUT_S,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return []

    if data.get("status") != "success":
        return []
    result = data.get("data", {}).get("result", [])
    if not result:
        return []
    series = result[0].get("values", [])
    parsed: list[tuple[float, float]] = []
    for ts, value in series:
        try:
            parsed.append((float(ts), float(value)))
        except (TypeError, ValueError):
            continue
    return parsed


def is_prometheus_reachable() -> bool:
    try:
        r = requests.get(f"{PROMETHEUS_URL}/-/ready", timeout=HTTP_TIMEOUT_S)
        return r.ok
    except requests.RequestException:
        return False


# ── Vistas agregadas que consumen los componentes del dashboard ────────────

def get_resumen() -> dict[str, Any]:
    """
    KPIs para las tarjetas superiores del dashboard.

    - total = correos recibidos por recep (recep_processing_latency_seconds_count)
    - respondidos_auto = consultas atendidas por ragsv (llm_processing_latency_seconds_count)
    - tiempo_promedio_s = latencia end-to-end (e2e_resolution_latency_seconds), o sólo
      la del LLM si la métrica E2E aún no tiene observaciones.
    """
    total_7d = _query("sum(increase(recep_processing_latency_seconds_count[7d]))") or 0.0
    auto_7d = _query("sum(increase(llm_processing_latency_seconds_count[7d]))") or 0.0
    avg_latency = _query(
        "sum(rate(e2e_resolution_latency_seconds_sum[7d])) "
        "/ sum(rate(e2e_resolution_latency_seconds_count[7d]))"
    )
    if avg_latency is None:
        avg_latency = _query(
            "sum(rate(llm_processing_latency_seconds_sum[7d])) "
            "/ sum(rate(llm_processing_latency_seconds_count[7d]))"
        )

    total_int = int(round(total_7d))
    auto_int = int(round(auto_7d))
    derivados_int = max(0, total_int - auto_int)
    tasa = round((auto_int / total_int) * 100, 1) if total_int else 0.0
    tiempo_prom = round(avg_latency, 2) if avg_latency is not None else 0.0

    return {
        "total_7d": total_int,
        "respondidos_auto_7d": auto_int,
        "derivados_7d": derivados_int,
        "tasa_automatizacion": tasa,
        "tiempo_promedio_s": tiempo_prom,
        "prometheus_disponible": is_prometheus_reachable(),
    }


def get_serie_historica(dias: int = 30) -> list[dict[str, Any]]:
    """
    Serie diaria para el gráfico de líneas.

    Devuelve lista de {fecha (date), total, respondidos_auto, derivados, tiempo_promedio_s}.
    Si Prometheus no tiene datos suficientes, devuelve una serie de ceros para que
    el chart pueda renderizar el eje y la grilla.
    """
    end_ts = time.time()
    start_ts = end_ts - dias * 86400
    step = 86400  # 1 día

    auto_series = _query_range(
        "sum(increase(llm_processing_latency_seconds_count[1d]))",
        start_ts, end_ts, step,
    )
    total_series = _query_range(
        "sum(increase(recep_processing_latency_seconds_count[1d]))",
        start_ts, end_ts, step,
    )

    # Indexamos las dos series por fecha para alinearlas
    def _by_day(series: list[tuple[float, float]]) -> dict[date, float]:
        out: dict[date, float] = {}
        for ts, val in series:
            d = datetime.fromtimestamp(ts).date()
            out[d] = val
        return out

    auto_by_day = _by_day(auto_series)
    total_by_day = _by_day(total_series)

    hoy = datetime.now().date()
    salida: list[dict[str, Any]] = []
    for i in range(dias - 1, -1, -1):
        d = hoy - timedelta(days=i)
        total = int(round(total_by_day.get(d, 0.0)))
        auto = int(round(auto_by_day.get(d, 0.0)))
        derivados = max(0, total - auto)
        salida.append({
            "fecha": d,
            "total": total,
            "respondidos_auto": auto,
            "derivados": derivados,
            "tiempo_promedio_s": 0.0,
        })
    return salida


def get_grafana_url(path: str = "/") -> str:
    """URL de Grafana que se abre cuando el usuario hace clic en el botón."""
    if not path.startswith("/"):
        path = "/" + path
    return f"{GRAFANA_URL.rstrip('/')}{path}"

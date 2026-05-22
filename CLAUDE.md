# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**S.A.G.A** (Sistema de Apoyo y Gestión Académica) is an SOA-based system for UDP's Faculty of Engineering and Sciences (FIC). It automates incoming email triage and response using an LLM + RAG pipeline. The architecture revolves around an **Enterprise Service Bus (ESB)** that routes messages between independent Python services via TCP sockets.

## Infrastructure

Start the required infrastructure before running any service or client:

```bash
docker-compose up -d      # Start BUS (port 5001) and ChromaDB (port 8000)
docker-compose ps         # Check status
docker-compose logs -f    # Tail logs
docker-compose down       # Stop all
```

- **BUS**: `localhost:5001` (TCP) — image `jrgiadach/soabus:latest`
- **ChromaDB**: `http://localhost:8000` — vector database for RAG

## Service Communication Protocol (`shared/soa_lib.py`)

All services and clients communicate via a fixed-length framing protocol over TCP:

- **Message format**: `[5-byte length][5-char service name][payload]`
- Service names must be **exactly 5 characters** (e.g., `recep`, `class`, `ragsv`, `casos`, `docum`, `metri`).
- `send_message(sock, service_name, payload)` — sends a framed message.
- `receive_message(sock)` — reads the 5-byte length prefix, then reads that many bytes.
- On startup, every service sends `send_message(sock, "sinit", service_name)` to register with the BUS.

## Writing a New Service (`shared/service_base.py`)

Use `start_service(service_name, process_function)` from `shared.service_base`:

```python
from shared.service_base import start_service

def handle(request: dict) -> dict:
    # process and return a dict
    return {"status": "ok", "result": ...}

start_service("mysv", handle)
```

The base handles registration, the receive loop, JSON parse errors, and sending responses back through the BUS. `process_function` receives a `dict` and must return a `dict`.

## Portal Administrativo (Desktop Client)

Located in `client/portal-admin/`. A CustomTkinter desktop app for secretaría staff.

### Run

```bash
cd client/portal-admin
python -m venv venv && source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python main.py
```

### Build executable

```bash
pip install pyinstaller
python build.py
# Output: dist/SAGA/ (SAGA.exe on Windows, SAGA on macOS/Linux)
```

### Architecture of the portal

- `main.py` — `SAGAApp` (CTk root window), view routing via `_navigate(view_name)`
- `theme.py` — all visual constants (colors, font sizes, spacing); UDP institutional palette (`UDP_RED = #C0272D`)
- `data/db.py` — **currently an in-memory mock**; production will replace it with HTTP calls to services CS-01 (documents), CS-07 (metrics), CS-08 (errors). Data layer is intentionally isolated so only `data/db.py` needs changing.
- `components/` — reusable widgets: `Sidebar`, `KPICard`, `LineChartCard`, `DonutChartCard`
- `views/` — full-page views: `DashboardView`, `DocumentosView`

Charts use native `tkinter.Canvas` — no matplotlib dependency.

## Planned Services (not yet implemented)

Per the project spec in `README.md`, the services folder will contain:

| Name  | Service | Key tech |
|-------|---------|----------|
| `recep` | Email reception | — |
| `class` | LLM classifier | — |
| `ragsv` | RAG generator | ChromaDB vector store |
| `casos` | Case management | PostgreSQL |
| `docum` | Document management | PostgreSQL |
| `metri` | Metrics & audit | PostgreSQL |

Database schema (PostgreSQL with pgvector) is specified in `README.md`.

## Key Constraints

- Service names must be exactly 5 characters or `start_service` raises `ValueError`.
- `ctk.set_appearance_mode()` and `ctk.set_default_color_theme()` must be called before creating any widget (macOS requirement, already done in `main.py`).
- `corner_radius=0` on `CTkScrollableFrame` causes a macOS rendering bug — use `1` instead.
- The portal's `_navigate` defers the first view by 120 ms (`self.after(120, ...)`) to ensure the window is fully laid out on macOS before widgets are placed.

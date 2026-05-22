# SAGA · Portal Administrativo (Desktop)

Aplicación de escritorio para la Secretaría de Estudios de la Facultad de Ingeniería y Ciencias — Universidad Diego Portales.

Componente **Portal Administrativo** dentro de la arquitectura SOA del Sistema de Apoyo y Gestión Académica (SAGA). Permite:

- **Cargar y gestionar documentos institucionales** (Reglamentos, mallas, calendarios, FAQ, procedimientos).
- **Visualizar métricas de rendimiento** del sistema de respuesta automatizada de correos.
- **Consultar la actividad reciente** de procesamiento de correos.

---

## Requerimientos satisfechos

| Código | Descripción |
|--------|-------------|
| RF01   | Carga de documentos |
| RF04   | Actualización / eliminación de documentos |
| RF11   | Visualización de métricas de desempeño |

---

## Stack técnico

- **Python**
- **CustomTkinter** — framework de UI moderno basado en Tkinter
- **PyInstaller** — empaquetado a ejecutable nativo

---

## Cómo ejecutar la aplicación

### 1. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate         # macOS / Linux
venv\Scripts\activate            # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación

```bash
python main.py
```

La aplicación abrirá una ventana de escritorio con la identidad institucional UDP.

---

## Cómo generar el ejecutable

Para distribuir la aplicación sin necesidad de tener Python instalado:

```bash
pip install pyinstaller
python build.py
```

Esto genera:

- **Windows:** `dist/SAGA/SAGA.exe`
- **macOS:** `dist/SAGA/SAGA.app`

La carpeta `dist/SAGA/` completa puede entregarse al usuario final. No requiere instalación.

---

## Integración con los otros servicios

En la versión final de SAGA, el módulo `data/db.py` se reemplaza por un cliente HTTP que consume:

| Servicio externo | Endpoint | Función |
|------------------|----------|---------|
| **CS-01** Gestión de Documentos | `POST /docs/upload`, `GET /docs`, `PUT /docs/{id}` | Persistencia real |
| **CS-07** Métricas | `GET /metricas/resumen`, `GET /metricas/historico` | Métricas en tiempo real |
| **CS-08** Gestión de Errores | `GET /errores` | Logs de errores |

La arquitectura de la aplicación está diseñada para que esa migración requiera cambios solo dentro de `data/db.py`, sin tocar las vistas ni los componentes.

---
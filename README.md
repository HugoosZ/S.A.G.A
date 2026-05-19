# S.A.G.A

## Idea de estructura:

```
S.A.G.A/
│
├── .gitignore
├── README.md
│
├── bus/                               # Componente Central: Enterprise Service Bus (ESB)
│   ├── soa_bus.py                     # Orquestador principal de conexiones por sockets
│   └── soa_lib.py                     # Funciones compartidas de red (send/receive)
│
├── shared/                            # Capa compartida de datos y utilidades comunes
│   ├── __init__.py
│   └── database.py                    # Configuración de persistencia (PostgreSQL)
│
├── services/                          # COMPONENTES DE SERVICIO (Taxonomía Oficial)
│   ├── recep/                         # Servicio de Gestión de Recepción de Correos
│   │   ├── main.py
│   │   └── utils.py
│   ├── class/                         # Servicio de Clasificación con LLM
│   │   ├── main.py
│   │   └── classifier.py
│   ├── ragsv/                         # Servicio de Generación Aumentada por Recuperación (RAG)
│   │   ├── main.py
│   │   └── vector_store.py            # Gestión de Base de Datos Vectorial
│   ├── casos/                         # Servicio de Gestión de Casos
│   │   └── main.py
│   ├── docum/                         # Servicio de Gestión de Documentos
│   │   └── main.py
│   └── metri/                         # Servicio de Métricas y Auditoría
│       └── main.py
│
└── clients/                           # COMPONENTES CLIENTE
    ├── monitor_agente/                # Agente Monitor de Correo Entrante (Segundo plano)
    │   └── main.py
    └── portal_web/                    # Portal de Administración Web (Interfaz Gráfica)
        ├── main.py                    # Backend del Portal (FastAPI / Flask que actúa como Gateway)
        ├── static/                    # Archivos estáticos (CSS, JS)
        └── templates/                 # Plantillas HTML
```

## Propuesta de entidades para el entorno vectorial

```sql
-- 1. Usuario
CREATE TABLE Usuario (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(150),
    email VARCHAR(255),
    rol VARCHAR(30),
    activo BOOLEAN,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Documento
CREATE TABLE Documento (
    id_documento SERIAL PRIMARY KEY,
    nombre VARCHAR(255),
    tipo VARCHAR(50),
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ruta_archivo TEXT,
    texto_extraido TEXT,
    estado VARCHAR(20),
    id_usuario INTEGER,
    embedding vector(1536),
    CONSTRAINT fk_usuario_doc FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
);

-- 3. Hilo
CREATE TABLE Hilo (
    id_hilo SERIAL PRIMARY KEY,
    asunto_original VARCHAR(255),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20),
    remitente_email VARCHAR(255)
);

-- 4. Correo
CREATE TABLE Correo (
    id_correo SERIAL PRIMARY KEY,
    id_hilo INTEGER,
    remitente VARCHAR(255),
    asunto VARCHAR(255),
    cuerpo TEXT,
    fecha_recepcion TIMESTAMP,
    estado VARCHAR(20),
    clasificacion VARCHAR(100),
    num_consultas INTEGER,
    CONSTRAINT fk_hilo_correo FOREIGN KEY (id_hilo) REFERENCES Hilo(id_hilo)
);

-- 5. Respuesta
CREATE TABLE Respuesta (
    id_respuesta SERIAL PRIMARY KEY,
    id_correo INTEGER,
    id_documento INTEGER,
    contenido TEXT,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo VARCHAR(20),
    fuente TEXT,
    enviado_por INTEGER,
    CONSTRAINT fk_correo_resp FOREIGN KEY (id_correo) REFERENCES Correo(id_correo),
    CONSTRAINT fk_documento_resp FOREIGN KEY (id_documento) REFERENCES Documento(id_documento),
    CONSTRAINT fk_usuario_resp FOREIGN KEY (enviado_por) REFERENCES Usuario(id_usuario)
);

-- 6. Historial Consulta
CREATE TABLE Historial_Consulta (
    id_historial SERIAL PRIMARY KEY,
    correo_usuario VARCHAR(255),
    id_correo INTEGER,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resuelto BOOLEAN,

```
```bash
docker pull jrgiadach/soabus:latest

    num_intentos INTEGER,
    CONSTRAINT fk_correo_hist FOREIGN KEY (id_correo) REFERENCES Correo(id_correo)
);
```

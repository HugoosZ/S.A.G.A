# S.A.G.A

## Idea de estructura:

```
S.A.G.A/
│
├── .gitignore
├── README.md
├── requirements.txt
│
├── bus/                               # Componente Central: Enterprise Service Bus (ESB)
│   ├── soa_bus.py                     # Orquestador principal de conexiones por sockets
│   └── soa_lib.py                     # Funciones compartidas de red (send/receive)
│
├── shared/                            # Capa compartida de datos y utilidades comunes
│   ├── __init__.py
│   ├── database.py                    # Configuración de persistencia (PostgreSQL)
│   ├── service_base.py                # Clase base para todos los servicios
│   └── soa_lib.py                     # Funciones de comunicación SOA
│
├── packages/                          # PAQUETES REUTILIZABLES
│   └── rag_core/                      # Core del sistema RAG (Retrieval-Augmented Generation)
│       ├── data/                      # Procesamiento y gestión de datos
│       │   ├── ingestion.py           # Ingestión de documentos en ChromaDB
│       │   ├── chunking.py            # División de texto en chunks
│       │   └── marker.py              # Extracción de texto con OCR (Marker)
│       ├── models/                    # Modelos y clientes de IA
│       │   └── embeddings.py          # Cliente de embeddings (Google Generative AI)
│       └── utils/                     # Utilidades compartidas
│           ├── config.py              # Configuración centralizada
│           └── logger.py              # Sistema de logging
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
│   │   ├── main.py
│   │   ├── Dockerfile                 # Containerización del servicio
│   │   └── test_docum_client.py       # Cliente de pruebas
│   └── metri/                         # Servicio de Métricas y Auditoría
│       └── main.py
│
├── data/                              # Base de datos de persistencia
│   └── chroma_data/                   # Base de datos vectorial (ChromaDB)
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
    num_intentos INTEGER,
    CONSTRAINT fk_correo_hist FOREIGN KEY (id_correo) REFERENCES Correo(id_correo)
);
```

## Infraestructura con Docker Compose

El proyecto incluye un archivo `docker-compose.yml` para levantar los servicios base:

- `saga-bus`
    - Imagen: `jrgiadach/soabus:latest`
    - Contenedor: `saga-bus-container`
    - Plataforma: `linux/amd64`
    - Puerto: `5001` (host) -> `5000` (contenedor)

- `saga-chromadb`
    - Imagen: `chromadb/chroma:latest`
    - Contenedor: `saga-chroma-container`
    - Puerto: `8000` (host) -> `8000` (contenedor)
    - Volumen persistente: `./data/chroma_data:/data`
    - Variables:
        - `IS_PERSISTENT=TRUE`
        - `ANONYMIZED_TELEMETRY=FALSE`

Ambos servicios comparten la red de Docker `saga-network` y usan `restart: unless-stopped`.

### Comandos utiles

Levantar servicios:

```bash
docker-compose up -d
```

Ver estado:

```bash
docker-compose ps
```

Ver logs:

```bash
docker-compose logs -f
```

Detener servicios:

```bash
docker-compose down
```

### Acceder a servicios

Verificar contenedores activos:

```bash
docker ps
```

Entrar al contenedor del BUS:

```bash
docker exec -it saga-bus-container /bin/sh
```

Entrar al contenedor de ChromaDB:

```bash
docker exec -it saga-chroma-container /bin/sh
```

Probar acceso HTTP a ChromaDB desde host:

```bash
curl http://localhost:8000/api/v1/heartbeat
```

Notas de acceso:

- BUS: expuesto en `localhost:5001` (TCP).
- ChromaDB: expuesto en `http://localhost:8000`.

Si solo necesitas descargar la imagen del BUS manualmente:

```bash
docker pull jrgiadach/soabus:latest
```
Ejecución de test:
```bash
docker exec -it saga-service-docum /bin/sh
python -m services.docum.test_docum_client
```

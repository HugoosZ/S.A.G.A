# RAGSV — Servicio de Generación Aumentada por Recuperación

> 🤖 **Made by AI**

> **Nombre en el BUS:** `ragsv` (5 caracteres)  
> **Rol:** Recibe una pregunta en lenguaje natural, recupera contexto relevante de ChromaDB y genera una respuesta con un LLM (Gemini/Gemma).

---

## Tabla de Contenidos

1. [Arquitectura Interna](#arquitectura-interna)
2. [Entrada (Request)](#entrada-request)
3. [Salida (Response)](#salida-response)
4. [Estructura del campo `answer`](#estructura-del-campo-answer)
5. [Cómo extraer la respuesta desde otro servicio](#cómo-extraer-la-respuesta-desde-otro-servicio)
6. [Ejecución y testing manual](#ejecución-y-testing-manual)
7. [Referencia de módulos internos](#referencia-de-módulos-internos)
8. [Variables de entorno](#variables-de-entorno)

---

## Arquitectura Interna

```text
┌─────────────┐     JSON/BUS      ┌────────────────┐
│  Cliente /   │ ──────────────▶  │   main.py      │
│  Otro Svc    │                  │  (ragsv)       │
└─────────────┘                   └───────┬────────┘
                                          │ (engine=standard|react)
                       ┌──────────────────┴──────────────────┐
                       ▼                                     ▼
             ┌─────────────────┐                   ┌─────────────────┐
             │    qa.py         │                   │    ReAct.py      │
             │ answer_with_rag()│                   │ run_react_agent()│
             └────────┬────────┘                   └────────┬────────┘
                      │                                     │
                      └───────────────────┬─────────────────┘
                                          ▼
                   ┌────────────┐ ┌────────────┐ ┌────────────┐
                   │retriever.py│ │  llm.py    │ │ (hybrid)   │
                   │ ChromaDB   │ │  Agent()   │ │ KG (opt.)  │
                   └────────────┘ └────────────┘ └────────────┘
```

**Flujo de una petición:**

1. El BUS entrega el payload JSON ya parseado como `dict` a `process_request()` en `main.py`.
2. `main.py` lee el parámetro `engine` y enruta la pregunta al RAG Estándar (`qa.py`) o al Agente Autónomo (`ReAct.py`).
3. `qa.py` utiliza `retriever.py` para buscar los fragmentos más relevantes en ChromaDB (con reranking opcional).
4. Se construye un prompt con el contexto recuperado y se envía al LLM vía `llm.py` (`Agent.generate()`).
5. La respuesta del LLM se empaqueta en un `dict` y se retorna al BUS.

---

## Entrada (Request)

El payload JSON que debe enviarse al servicio `ragsv` a través del BUS desde cualquier otro microservicio:

```json
{
  "question": "¿De qué trata el Proyecto de Arquitectura de Software?",
  "k": 4,
  "collection_name": "study_collection",
  "engine": "standard"
}
```

| Campo             | Tipo   | Obligatorio | Descripción                                                          |
|-------------------|--------|:-----------:|----------------------------------------------------------------------|
| `question`        | `str`  | ✅          | La pregunta en lenguaje natural.                                     |
| `k`               | `int`  | ❌          | Número de fragmentos a recuperar (default: `4`).                     |
| `collection_name` | `str`  | ❌          | Colección de ChromaDB a consultar (default: `study_collection`).     |
| `engine`          | `str`  | ❌          | Motor cognitivo a usar: `"standard"` o `"react"` (default: `"standard"`). |

---

## Salida (Response)

### Respuesta exitosa

```json
{
  "status": "success",
  "answer": [ ... ],
  "tokens_used": 1324,
  "query_type": "vector_only",
  "sources_used": ["chroma_db"],
  "files_focus": []
}
```

| Campo          | Tipo          | Descripción                                                                         |
|----------------|---------------|-------------------------------------------------------------------------------------|
| `status`       | `str`         | `"success"` o `"error"`.                                                            |
| `answer`       | `list[dict]`  | **Lista de bloques de contenido** generados por el LLM. Ver [sección detallada](#estructura-del-campo-answer). |
| `tokens_used`  | `int`         | Tokens estimados consumidos en el prompt (no incluye la respuesta).                 |
| `query_type`   | `str`         | Tipo de búsqueda usada: `"vector_only"` o `"hybrid"`.                               |
| `sources_used` | `list[str]`   | Fuentes de datos consultadas (ej. `["chroma_db"]`).                                 |
| `files_focus`  | `list[str]`   | Archivos que fueron priorizados si la pregunta mencionaba un documento específico.   |

### Respuesta de error

```json
{
  "status": "error",
  "message": "El payload debe contener la clave 'question'."
}
```

---

## Estructura del campo `answer`

> ⚠️ **Importante:** El campo `answer` **no es un string**. Es una **lista de bloques de contenido** (`list[dict]`).

El LLM puede devolver múltiples bloques. Cada bloque tiene un campo `type` que indica su naturaleza:

### Bloque `thinking` (razonamiento interno)

```json
{
  "type": "thinking",
  "thinking": "Análisis interno del modelo sobre cómo construir la respuesta..."
}
```

- Contiene el **proceso de razonamiento** del modelo (chain-of-thought).
- **No debe mostrarse al usuario final.** Es útil para debug y auditoría.

### Bloque `text` (respuesta final)

```json
{
  "type": "text",
  "text": "El proyecto trata sobre el diseño arquitectónico del **Sistema de Apoyo y Gestión Académica (SAGA)**..."
}
```

- Contiene la **respuesta legible** que debe presentarse al usuario.
- Incluye formato Markdown (negritas, listas numeradas, sección FUENTES).

### Ejemplo real de `answer`

```json
[
  {
    "type": "thinking",
    "thinking": "Pedagogical Assistant.\nAnswer precisely and concisely..."
  },
  {
    "type": "text",
    "text": "El proyecto trata sobre el diseño arquitectónico del **Sistema de Apoyo y Gestión Académica (SAGA)**.\n\nFUENTES\n* Proyecto_Arquitectura_de_Software.pdf | chunk=17\n* Proyecto_Arquitectura_de_Software.pdf | chunk=5"
  }
]
```

---

## Personalidad del RAG y Reglas de Derivación (Secretaría Virtual)

El asistente virtual está configurado a través del `SYSTEM_INSTRUCTIONS` (en `qa.py`) para actuar como un **primer filtro de la Secretaría de Estudios de la UDP**. Se rige por las siguientes reglas de respuesta:

1. **Gestión Académica Resolutiva:** Responde de manera clara y basada en los documentos si hay información suficiente en el contexto recuperado.
2. **Flag `DERIVAR A SECRETARIA`:** Si la consulta académica requiere intervención humana (ej. revisión de un caso particular, firmas, excepciones) o la información no está en los reglamentos, el LLM iniciará su texto exactamente con la frase `DERIVAR A SECRETARIA`. El cliente (frontend u otro servicio) puede buscar este "flag" al principio de la respuesta para derivar automáticamente el ticket o chat al personal humano.
3. **Preguntas triviales sobre la UDP:** Si preguntan cosas cotidianas (ej. *¿dónde está la cafetería?* o *¿hay un Starbucks cerca de la facultad?*), el bot responderá de forma amable usando su conocimiento general sin derivar a secretaría.
4. **Preguntas ajenas (fuera de contexto):** Si preguntan por el clima o le piden programar código, el bot rechazará la solicitud aclarando su propósito netamente universitario. Tampoco derivará estas dudas a secretaría.

### Ejemplo de respuesta con derivación

```json
[
  {
    "type": "text",
    "text": "DERIVAR A SECRETARIA\nEl estudiante está solicitando una excepción a la regla de asistencia del Artículo 4, lo cual requiere evaluación directa de la Dirección de Carrera."
  }
]
```

---

## Cómo extraer la respuesta desde otro servicio

Cuando otro microservicio de SAGA consume la respuesta de `ragsv`, debe:

1. **Parsear el JSON** de la respuesta del BUS (saltando el prefijo de enrutamiento).
2. **Filtrar los bloques** de `answer` para obtener solo los de tipo `"text"`.

### Ejemplo en Python (dentro de otro servicio)

```python
import json

def extraer_respuesta_ragsv(raw_response: bytes) -> str:
    """
    Extrae el texto útil de la respuesta cruda del BUS para el servicio ragsv.
    
    Args:
        raw_response: bytes crudos recibidos del BUS (ej: b'ragsvOK{"status":...}')
    
    Returns:
        String con la respuesta legible del LLM, o un mensaje de error.
    """
    decoded = raw_response.decode('utf-8', errors='ignore')
    
    # 1. Localizar el inicio del JSON (saltar prefijo del BUS: "ragsvOK")
    json_start = decoded.find('{')
    if json_start == -1:
        return f"Error: No se encontró JSON en la respuesta. Raw: {decoded}"
    
    parsed = json.loads(decoded[json_start:])
    
    # 2. Verificar status
    if parsed.get("status") != "success":
        return f"Error del servicio: {parsed.get('message', 'Sin detalle')}"
    
    # 3. Extraer solo los bloques de tipo "text" del answer
    answer_blocks = parsed.get("answer", [])
    
    # Si answer es un string directo (modelos sin thinking), retornar tal cual
    if isinstance(answer_blocks, str):
        return answer_blocks
    
    # Filtrar bloques de tipo "text" e ignorar los de tipo "thinking"
    text_parts = []
    for block in answer_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(block.get("text", ""))
    
    if not text_parts:
        return "No se obtuvo respuesta de texto del LLM."
    
    return "\n".join(text_parts)
```

### Uso desde un servicio

```python
from shared.soa_lib import connect_to_bus, send_message, receive_message
import json

# Enviar pregunta a ragsv
sock = connect_to_bus()
payload = json.dumps({"question": "¿Cuál es el objetivo del proyecto?"})
send_message(sock, "ragsv", payload)

# Recibir y extraer
raw = receive_message(sock)
respuesta_limpia = extraer_respuesta_ragsv(raw)
print(respuesta_limpia)
# >>> "El proyecto trata sobre el diseño arquitectónico del **SAGA**..."

sock.close()
```

### Acceso a metadatos adicionales

```python
# Después de parsear el JSON:
parsed = json.loads(decoded[json_start:])

tokens   = parsed.get("tokens_used")       # int: tokens consumidos
q_type   = parsed.get("query_type")         # str: "vector_only" | "hybrid"
sources  = parsed.get("sources_used")       # list: ["chroma_db"]
focus    = parsed.get("files_focus")        # list: archivos priorizados
```

---

## Ejecución y testing manual

### Levantar el servicio con Docker Compose

```bash
docker compose up -d --build service-ragsv
```

### Ejecutar el cliente de prueba

```bash
docker exec -it saga-service-ragsv python -m services.ragsv.test_ragsv_client
```

### Ver logs en tiempo real

```bash
docker logs -f saga-service-ragsv
```

---

## Referencia de módulos internos

### `services/ragsv/main.py`

Punto de entrada del microservicio. Registra `ragsv` en el BUS y delega cada petición a `process_request()`, que:
- Valida que el payload contenga `question`.
- Invoca `answer_with_rag()` del motor RAG.
- Retorna un `dict` que `service_base` serializa automáticamente a JSON.

### `services/ragsv/test_ragsv_client.py`

Cliente de prueba que se conecta al BUS, envía una pregunta hardcoded a `ragsv` y muestra la respuesta parseada en consola. Útil para validar el servicio end-to-end desde dentro del contenedor.

---

### `packages/rag_core/rag/qa.py`

Módulo central de preguntas y respuestas. Contiene:

| Función                     | Responsabilidad                                                                 |
|-----------------------------|---------------------------------------------------------------------------------|
| `answer_with_rag()`         | Orquesta todo el pipeline: recuperación → priorización → prompt → LLM.         |
| `build_prompt()`            | Construye el prompt con contexto recuperado, respetando el límite de tokens.    |
| `build_hybrid_prompt()`     | Variante para búsqueda híbrida (grafo de conocimiento + vectores).             |
| `extract_mentioned_files()` | Detecta si la pregunta menciona archivos específicos para priorizarlos.         |
| `prioritize_docs_by_source()`| Reordena los documentos recuperados dando prioridad a archivos mencionados.   |

### `packages/rag_core/rag/ReAct.py`

Agente autónomo para consultas complejas:

| Función / Tool              | Responsabilidad                                                                 |
|-----------------------------|---------------------------------------------------------------------------------|
| `create_react_agent()`      | Inicializa el agente Langchain `zero-shot-react-description` con herramientas.  |
| `run_react_agent()`         | Ejecuta el razonamiento del agente, controlando el presupuesto de tokens.       |
| `saga_search_tool()`        | Herramienta interna del agente para hacer búsquedas híbridas (Grafo+Vectores).  |

### `packages/rag_core/rag/retriever.py`

Módulo de recuperación de documentos:

| Función               | Responsabilidad                                                                      |
|-----------------------|--------------------------------------------------------------------------------------|
| `get_vectorstore()`   | Se conecta a ChromaDB vía HTTP y retorna un vectorstore de LangChain.                |
| `get_relevant_docs()` | Recupera los `k` fragmentos más relevantes, con reranking por coseno si está habilitado. |

### `packages/rag_core/models/llm.py`

Wrapper del LLM:

| Clase / Método      | Responsabilidad                                                                   |
|----------------------|-----------------------------------------------------------------------------------|
| `Agent.__init__()`   | Inicializa `ChatGoogleGenerativeAI` con modelo, temperatura y max tokens.         |
| `Agent.generate()`   | Invoca el LLM con un prompt y retorna el contenido de la respuesta.               |

**Modelo por defecto:** `gemma-4-26b-a4b-it` (configurable vía `LLM_MODEL`).

---

## Variables de entorno

Variables que afectan el comportamiento de `ragsv` (definidas en `.env` o en `docker-compose.yml`):

| Variable                  | Default                    | Descripción                                         |
|---------------------------|----------------------------|-----------------------------------------------------|
| `GOOGLE_API_KEY`          | —                          | API key de Google Generative AI **(obligatoria)**.   |
| `BUS_HOST`                | `saga-bus`                 | Host del BUS SOA.                                    |
| `BUS_PORT`                | `5000`                     | Puerto del BUS SOA.                                  |
| `CHROMA_HOST`             | `saga-chromadb`            | Host del contenedor de ChromaDB.                     |
| `LLM_MODEL`               | `gemma-4-26b-a4b-it`      | Modelo LLM a utilizar.                               |
| `EMBEDDING_MODEL`         | `gemini-embedding-2-preview`| Modelo de embeddings.                               |
| `DEFAULT_TOP_K`           | `15`                       | Documentos a recuperar por defecto.                  |
| `RERANK_ENABLED`          | `true`                     | Habilitar reranking por similitud de coseno.         |
| `DEFAULT_COLLECTION_NAME` | `study_collection`         | Colección por defecto en ChromaDB.                   |
| `GRAPH_HYBRID_SEARCH`     | `true`                     | Habilitar búsqueda híbrida (grafo + vector).         |
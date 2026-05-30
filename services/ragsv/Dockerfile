# services/ragsv/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Copiar e instalar dependencias globales
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. COPIAS QUIRÚRGICAS: Copiar solo lo que necesita este microservicio
COPY shared/ ./shared/
COPY packages/rag_core/ ./packages/rag_core/
COPY services/ragsv/ ./services/ragsv/

# Ejecutar el servicio resolviendo los paths desde la raíz /app
CMD ["python", "-m", "services.ragsv.main"]
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN pip install psycopg2-binary

# Copiar el archivo de requerimientos si existe, de lo contrario copiar todo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY shared/ ./shared/
COPY services/recep/ ./services/recep/

CMD ["python", "services/recep/main.py"]
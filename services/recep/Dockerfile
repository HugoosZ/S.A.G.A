FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install psycopg2-binary

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY shared/ ./shared/
COPY services/recep/ ./services/recep/

CMD ["python", "-m", "services.recep.main"]
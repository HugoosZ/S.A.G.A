FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Copiar librerías necesarias
RUN pip install imapclient

COPY shared/ /app/shared/
COPY clients/monitor_agente/ /app/clients/monitor_agente/

CMD ["python", "clients/monitor_agente/main.py"]
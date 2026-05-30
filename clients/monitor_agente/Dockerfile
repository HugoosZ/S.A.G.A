FROM python:3.10-slim

WORKDIR /app

COPY clients/monitor_agente/requirements.txt ./clients/monitor_agente/
RUN pip install --no-cache-dir -r clients/monitor_agente/requirements.txt

COPY shared/ ./shared/
COPY clients/monitor_agente/ ./clients/monitor_agente/

ENV PYTHONPATH=/app

CMD ["python", "-u", "clients/monitor_agente/main.py"]
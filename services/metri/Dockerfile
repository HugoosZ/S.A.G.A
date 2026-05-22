FROM python:3.10-slim

WORKDIR /app

COPY services/metri/requirements.txt ./services/metri/
RUN pip install --no-cache-dir -r services/metri/requirements.txt

COPY shared/ ./shared/
COPY services/metri/ ./services/metri/

ENV PYTHONPATH=/app

CMD ["python", "-u", "services/metri/main.py"]
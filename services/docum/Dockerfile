FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY packages/rag_core/ ./packages/rag_core/

COPY services/docum/ ./services/docum/

CMD ["python", "-m", "services.docum.main"]
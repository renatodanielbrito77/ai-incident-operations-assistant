FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

COPY investigation_models.py .

COPY search_qdrant.py .

COPY context_rules.py .

COPY history_rules.py .

COPY evidence_rules.py .

COPY audit.py .

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

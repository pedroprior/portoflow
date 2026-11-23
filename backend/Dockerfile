FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Sobe do zero: aplica as migrations, carrega o seed (idempotente) e inicia a API.
CMD ["sh", "-c", "alembic upgrade head && python seed.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
RUN useradd --create-home --uid 10001 app && mkdir -p /app/data/uploads && chown -R app:app /app
EXPOSE 8000

FROM base AS runtime
USER app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

FROM base AS models
USER root
COPY backend/requirements-models.txt ./requirements-models.txt
RUN pip install --no-cache-dir -r requirements-models.txt
USER app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]


# Build locally first. Deployment requires Director approval and user authorization.
FROM node:22.13.0-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN VITE_SYNTHETIC_HOSTED=true npm run build

FROM python:3.11.6-slim-bookworm AS fixture
WORKDIR /app
COPY backend/requirements.txt backend/requirements-migrations.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements-migrations.txt
COPY backend/app ./backend/app
COPY backend/alembic.ini ./backend/alembic.ini
COPY backend/migrations ./backend/migrations
ENV PYTHONPATH=/app/backend PYTHONDONTWRITEBYTECODE=1
RUN mkdir /fixture && python -m app.demo.comprehensive --database /fixture/synthetic.sqlite3 > /fixture/manifest.json

FROM python:3.11.6-slim-bookworm AS runtime
WORKDIR /app
COPY backend/requirements.txt backend/requirements-migrations.txt ./backend/
# The fixture modules supplying retained IDs import the pinned migration package.
RUN pip install --no-cache-dir -r backend/requirements-migrations.txt && useradd --uid 10001 --create-home demo
COPY backend/app ./backend/app
COPY --from=frontend /build/dist ./frontend-dist
COPY --from=fixture --chown=10001:10001 /fixture /app/synthetic
ENV PYTHONPATH=/app/backend PYTHONDONTWRITEBYTECODE=1 \
    CLINRX_SYNTHETIC_DATABASE=/app/synthetic/synthetic.sqlite3 \
    CLINRX_SYNTHETIC_FRONTEND=/app/frontend-dist
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "app.demo.hosting:from_environment", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-proxy-headers", "--no-access-log"]

# Stage 1: Build the Svelte frontend
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# Stage 2: Python backend with built frontend
FROM --platform=$TARGETPLATFORM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc \
  gosu \
  passwd \
  && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY server/ ./

# Frontend dist -> static folder
COPY --from=frontend-builder /app/frontend/dist ./static

# Data dirs
RUN mkdir -p /app/data /config /media

# Default env — but PUID/PGID now OPTIONAL
ENV FLASK_APP=app.py \
  FLASK_ENV=production \
  PYTHONUNBUFFERED=1 \
  PORT=5000 \
  GUNICORN_WORKERS=1 \
  GUNICORN_THREADS=2 \
  GUNICORN_TIMEOUT=120

EXPOSE 5000


# ENTRYPOINT — now *does NOT require* PUID/PGID
# Safely strips quotes; only uses them if they exist and are valid numbers
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  '' \
  'echo "Sublogue - Docker image starting"' \
  'echo "Sublogue - Initializing container"' \
  '' \
  '# Clean quotes if Komodo/Portainer injects them' \
  'PUID_CLEAN=$(echo "$PUID" | tr -d "\"")' \
  'PGID_CLEAN=$(echo "$PGID" | tr -d "\"")' \
  '' \
  '# Only run UID/GID logic if BOTH are valid integers' \
  'if [ -n "$PUID_CLEAN" ] && [ -n "$PGID_CLEAN" ] && [ "$PUID_CLEAN" -eq "$PUID_CLEAN" ] 2>/dev/null && [ "$PGID_CLEAN" -eq "$PGID_CLEAN" ] 2>/dev/null; then' \
  '  echo "Sublogue - Running with PUID=$PUID_CLEAN PGID=$PGID_CLEAN"' \
  '  getent group "$PGID_CLEAN" >/dev/null 2>&1 || groupadd -g "$PGID_CLEAN" appgroup' \
  '  id -u "$PUID_CLEAN" >/dev/null 2>&1 || useradd -u "$PUID_CLEAN" -g "$PGID_CLEAN" -m appuser' \
  '  chown -R "$PUID_CLEAN:$PGID_CLEAN" /config /app/data /media || true' \
  '  exec gosu "$PUID_CLEAN:$PGID_CLEAN" "$@"' \
  'else' \
  '  echo "Sublogue - Running as root (no valid PUID/PGID provided)"' \
  'fi' \
  '' \
  'exec "$@"' \
  > /usr/local/bin/entrypoint.sh \
  && chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["sh", "-c", "echo \"Sublogue - Starting web server on port ${PORT}\"; gunicorn --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} app:app"]

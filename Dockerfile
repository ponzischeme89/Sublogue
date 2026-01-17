# Stage 1: Build the Svelte frontend
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with built frontend
FROM --platform=$TARGETPLATFORM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ ./

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Create data directories for SQLite database and user config
RUN mkdir -p /app/data /config /media

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PUID=
ENV PGID=
ENV GUNICORN_WORKERS=1
ENV GUNICORN_THREADS=2
ENV GUNICORN_TIMEOUT=120

# Expose port
EXPOSE 5000

# Entrypoint to handle optional PUID/PGID and low-memory defaults
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  '' \
  'echo \"Sublogue - Docker image starting\"' \
  'echo \"Sublogue - Initializing container\"' \
  'if [ -n \"$PUID\" ] && [ -n \"$PGID\" ]; then' \
  '  echo \"Sublogue - Running with PUID=$PUID PGID=$PGID\"' \
  '  if ! getent group \"$PGID\" >/dev/null 2>&1; then' \
  '    groupadd -g \"$PGID\" appgroup' \
  '  fi' \
  '  if ! id -u \"$PUID\" >/dev/null 2>&1; then' \
  '    useradd -u \"$PUID\" -g \"$PGID\" -m appuser' \
  '  fi' \
  '  chown -R \"$PUID\":\"$PGID\" /config /app/data /media 2>/dev/null || true' \
  '  exec gosu \"$PUID\":\"$PGID\" \"$@\"' \
  'fi' \
  'echo \"Sublogue - Running as root (PUID/PGID not set)\"' \
  '' \
  'exec \"$@\"' \
  > /usr/local/bin/entrypoint.sh \
  && chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Run with Gunicorn (tuned for low-memory hosts by default)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} app:app"]

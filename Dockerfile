# ── Stage 1: Build ───────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source
COPY . .

# Azure App Service uses PORT env var (default 8000), bot uses 3978
# We expose 3978 and let Azure route to it
EXPOSE 3978

# Azure App Service expects the app to bind to the PORT env variable
CMD ["python", "app.py"]

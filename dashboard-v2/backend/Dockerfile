# Dashboard V2 - Backend FastAPI
FROM python:3.12-slim

WORKDIR /app

# Installer les dependances systeme pour Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements et installer les dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Installer les navigateurs Playwright
RUN playwright install chromium --with-deps

# Creer utilisateur non-root
RUN useradd --create-home --shell /bin/bash appuser

# Copier le code de l'application
COPY --chown=appuser:appuser app/ ./app/

# Basculer vers utilisateur non-root
USER appuser

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Port expose
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande de demarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

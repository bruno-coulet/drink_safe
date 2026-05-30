# =========================================================================
# STAGE 1 : Préparation de l'environnement virtuel avec UV
# =========================================================================
FROM python:3.12-slim AS builder

# Récupération du binaire 'uv' depuis l'image officielle d'Astral-sh
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

# Optimisation du bytecode Python et définition du plan de travail
ENV UV_COMPILE_BYTECODE=1
WORKDIR /app

# Copie des fichiers de verrouillage du projet
COPY pyproject.toml uv.lock ./

# Synchronisation des dépendances de production (Debian Slim fournit /bin/sh et glibc)
RUN uv sync --frozen --no-dev --no-install-project

# =========================================================================
# STAGE 2 : Image de Production finale épurée
# =========================================================================
FROM python:3.12-slim

WORKDIR /app

# Injection de l'environnement virtuel dans le PATH système
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Récupération exclusive de l'environnement virtuel isolé créé au Stage 1
COPY --from=builder /app/.venv /app/.venv

# Copie de l'intégralité du code source unifié
COPY src/ /app/src/

# Exposition du port natif de notre API unique FastAPI
EXPOSE 8000

# Commande de démarrage industrielle avec Uvicorn
# pirge le cache
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
# Fichier : docker/mlflow/Dockerfile
FROM ghcr.io/mlflow/mlflow:v2.11.3

# Installation du driver PostgreSQL
RUN pip install --no-cache-dir psycopg2-binary

# Création explicite du répertoire des artéfacts et ouverture des droits
RUN mkdir -p /app/artifacts && chmod 777 /app/artifacts
FROM python:3.10-slim

# Installe 'uv' directement dans le conteneur depuis l'image officielle de astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Définit le dossier de travail dans le conteneur
WORKDIR /app


# --system permet d'installer directement dans l'environnement Python global du conteneur
RUN uv pip install --system mlflow scikit-learn

# On expose le port 5000 demandé pour le serveur MLflow
EXPOSE 5000

# Commande par défaut pour lancer le serveur MLflow
# Le host 0.0.0.0 est obligatoire pour que Docker communique avec ton Windows
# CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "./runs", "--default-artifact-root", "./artifacts"]
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "/runs", "--default-artifact-root", "/artifacts"]
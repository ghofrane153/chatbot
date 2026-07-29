FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p logs cache

# Exposer le port
EXPOSE 8001

# Lancer l'application
CMD uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}
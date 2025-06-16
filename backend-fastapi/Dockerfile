FROM python:3.13-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Créer les dossiers de stockage
RUN mkdir -p /app/storage/audio /app/storage/temp

# Copier le reste du code
COPY . .

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
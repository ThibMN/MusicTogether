FROM python:3.13-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    netcat-traditional \
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

# Rendre le script d'entrée exécutable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Exposer le port
EXPOSE 8000

# Utiliser le script d'entrée
ENTRYPOINT ["/entrypoint.sh"]
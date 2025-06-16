# MusicTogether Backend (FastAPI)

Ce dossier contient le backend FastAPI pour l'application MusicTogether.

## Structure du projet

```
backend-fastapi/
├── app/
│   ├── api/              # Routes API
│   │   ├── endpoints/    # Endpoints par fonctionnalité
│   │   └── routes.py     # Router principal
│   ├── db/               # Configuration de la base de données
│   ├── models/           # Modèles SQLAlchemy
│   ├── schemas/          # Schémas Pydantic
│   ├── main.py           # Point d'entrée de l'application
│   └── worker.py         # Tâches Celery
├── storage/              # Stockage des fichiers
│   ├── audio/            # Fichiers audio
│   └── temp/             # Fichiers temporaires
├── Dockerfile            # Configuration Docker
└── requirements.txt      # Dépendances Python
```

## Installation

### Avec Docker (recommandé)

Le backend est configuré pour fonctionner avec Docker. Utilisez la commande suivante depuis la racine du projet :

```bash
docker-compose up -d
```

### Sans Docker

1. Créez un environnement virtuel Python :

```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

3. Démarrez l'application :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Une fois l'application démarrée, vous pouvez accéder à la documentation Swagger à l'adresse suivante :

- http://localhost:8000/docs

## Fonctionnalités principales

- Gestion des utilisateurs (en coordination avec le service PHP)
- Gestion des salles d'écoute
- Téléchargement et streaming de musiques
- Gestion des files d'attente
- Chat en temps réel via WebSockets
- Playlists et favoris

## Tâches en arrière-plan

Les tâches lourdes comme le téléchargement de musiques sont gérées par Celery. Pour démarrer le worker Celery manuellement :

```bash
celery -A app.worker worker --loglevel=info
```

## Variables d'environnement

Les variables d'environnement suivantes peuvent être configurées :

- `DATABASE_URL` : URL de connexion à la base de données
- `REDIS_URL` : URL de connexion à Redis
- `CELERY_BROKER_URL` : URL du broker Celery
- `CELERY_RESULT_BACKEND` : URL du backend de résultats Celery 
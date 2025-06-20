# 🎶 MusicTogether

MusicTogether est une application web collaborative permettant à plusieurs utilisateurs d’écouter de la musique ensemble en temps réel, de discuter via un chat intégré, de gérer des files d’attente musicales et de créer des playlists partagées. Le projet s’inspire des plateformes de “listening party” et met l’accent sur la synchronisation, la simplicité d’utilisation et l’expérience communautaire.

## 🚀 Fonctionnalités principales

- Écoute synchronisée de musique en groupe (YouTube, fichiers uploadés…)
- Création de salles privées avec URL unique
- Chat textuel en temps réel dans chaque salle
- Gestion collaborative de la file d’attente musicale (drag & drop, suppression…)
- Historique d’écoutes, favoris, playlists personnelles
- Authentification (inscription/connexion) via PHP
- Interface moderne et responsive

## 🧱 Stack technique

### Frontend
- **Vue.js 3** (Composition API, Vite)
- **TailwindCSS** (UI responsive)
- **Pinia** (gestion d’état)
- **Howler.js** (lecture audio)
- **Color Thief JS** (extraction de couleurs des covers)

### Backend
- **FastAPI** (Python, API REST & WebSocket)
- **MariaDB** (base de données relationnelle, via SQLAlchemy)
- **Celery + Redis** (tâches asynchrones lourdes)
- **yt-dlp** & **ffmpeg** (téléchargement et traitement audio)

### Authentification
- **PHP** pour l’inscription/connexion (exigence pédagogique)
- **FastAPI** pour la gestion des tokens JWT, profils, etc.

### DevOps
- **Docker** & **docker-compose** (orchestration multi-conteneurs)
- **Déploiement** possible sur VPS, Render, Railway…

## 📦 Installation & Lancement rapide

### Prérequis

- [Docker](https://www.docker.com/) et [Docker Compose](https://docs.docker.com/compose/) installés

### Étapes

1. **Cloner le dépôt :**
   ```bash
   git clone https://github.com/ton-utilisateur/MusicTogether.git
   cd MusicTogether
   ```

2. **Lancer l’application :**
   ```bash
   docker-compose up --build
   ```
   Cela va :
   - Construire et lancer tous les services (frontend, backend, PHP, MariaDB, Redis…)
   - Installer automatiquement les dépendances nécessaires

3. **Accéder à l’application :**
   - Frontend : [http://localhost:8080](http://localhost:8080) (ou le port affiché dans les logs)
   - Backend API : [http://localhost:8000/docs](http://localhost:8000/docs) (documentation interactive FastAPI)
   - Interface d’authentification PHP : [http://localhost:8001](http://localhost:8001) (si configuré)

4. **Arrêter l’application :**
   ```bash
   docker-compose down
   ```

## 📝 Utilisation

- Crée un compte ou connecte-toi via l’interface d’authentification.
- Rejoins ou crée une salle pour écouter de la musique avec d’autres.
- Ajoute des musiques à la file d’attente (YouTube, upload…).
- Discute en temps réel via le chat intégré.
- Profite de la synchronisation automatique de la lecture !

## 📁 Structure du projet

- `frontend-vue/` : Application Vue.js (interface utilisateur)
- `backend-fastapi/` : API FastAPI (Python)
- `php-auth/` : Authentification (PHP)
- `mariadb-data/` : Données persistantes de la base MariaDB
- `docker-compose.yml` : Orchestration des services

## 🤝 Contribuer

Les contributions sont les bienvenues ! N’hésite pas à ouvrir une issue ou une pull request.

## 📄 Licence

Ce projet est sous licence MIT.
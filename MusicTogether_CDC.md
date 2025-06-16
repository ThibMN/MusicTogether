# 🎧 Cahier des charges — MusicTogether (Stack Vue.js/FastAPI/PHP)

---

## 🧱 Structure technique globale

### Frontend
- **Framework principal** : Vue.js 3 (Composition API) avec Vite
- **Style & UI** :
  - TailwindCSS (design responsive & rapide)
  - Color Thief JS (extraction de couleurs des covers)
  - Butterchurn (visualiseur audio réactif)
- **State Management** : Pinia (store centralisé léger et réactif)
- **Audio** :
  - Howler.js pour la lecture audio
- **Synchro / Realtime client** :
  - WebSocket natifs intégrés pour synchro musique & chat

### Backend
- **API principale** : FastAPI (Python)
  - REST pour toutes les routes classiques (musiques, salles, queue…)
  - WebSockets intégrés pour synchronisation en temps réel (lecture audio, chat, file)
- **Téléchargement & traitement audio** :
  - yt-dlp : récupération de musiques
  - ffmpeg : extraction/conversion si nécessaire
- **Base de données** : MariaDB (avec SQLAlchemy comme ORM)
- **Async / Tâches lourdes** :
  - asyncio pour les tâches légères
  - Celery + Redis pour les tâches lourdes (scan de métadonnées, conversion longue)

### Authentification
- **Inscription / Connexion** : gérées **en PHP uniquement** (contraintes école)
- **Le reste de l’authentification** (tokens JWT, vérifications, refresh, profils, etc.) : géré via **FastAPI**

### Infra / DevOps
- Docker + docker-compose pour orchestrer :
  - Vue.js
  - FastAPI
  - PHP
  - MariaDB
  - Redis (si besoin pour Celery)
- Déploiement possible via VPS / Render / Railway

---

## 🔐 Fonctionnalités utilisateur

### Comptes
- Inscription / Connexion (via PHP)
- Historique d’écoutes
- Favoris & playlists
- Connexion Last.fm (optionnel)
- Import de playlists (Spotify / YouTube)

### Salles
- URL unique par salle (ex: https://musictogether.com/room/ABCD)
- Chaque salle a :
  - Sa propre file d’attente
  - Son propre chat
  - Sa propre lecture audio synchronisée
- Gestion des utilisateurs en temps réel dans chaque salle

---

## 🎵 Page de lecture

- Interface type Figma [wireframe](https://www.figma.com/design/i6prsnwMHuNqgtnjCotO7M/MusicTogether?node-id=0-1&t=tp4dt16jIZmv1x91-1)
- **Éléments clés** :
  - Cover du morceau au centre
  - Boutons Skip / Repeat
  - Barre de recherche en haut (ajout musique à la queue)
  - Upload audio (scan auto des métadonnées)
  - File d’attente (panneau latéral droit)
  - Chat textuel (panneau latéral gauche)
  - Visualizer (Butterchurn) en fond, synchronisé à la musique
  - Couleurs extraites dynamiquement de la cover via Color Thief

---

## 📋 File d’attente

- Interface type Apple Music
- Draggable : permet de réordonner la queue
- Suppression simple avec bouton sur chaque ligne
- Chaque item :
  - Cover à gauche
  - Nom, auteur, date à droite

---

## 💬 Chat textuel

- Panneau latéral gauche
- Zone de saisie avec limite de 200 caractères
- Envoi via bouton ou touche Entrée
- Affichage : `pseudo: message` (pseudo coloré, message en blanc)

---

## 📡 Lecture audio & synchro

- Pré-téléchargement des musiques via yt-dlp
- Audio local sur le serveur, streamé en continu avec StreamingResponse
- WebSocket pour :
  - Synchronisation exacte de la lecture
  - Contrôle lecture/pause entre clients
  - Mise à jour live de la queue et du chat
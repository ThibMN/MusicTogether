# MusicTogether Frontend (Vue.js)

Ce dossier contient le frontend Vue.js pour l'application MusicTogether.

## Structure du projet

```
frontend-vue/
├── src/
│   ├── assets/           # Images, fonts, etc.
│   │   ├── ChatPanel.vue
│   │   ├── MusicPlayer.vue
│   │   ├── QueuePanel.vue
│   │   └── SearchBar.vue
│   ├── stores/           # Stores Pinia
│   │   ├── chat.ts
│   │   ├── music.ts
│   │   ├── queue.ts
│   │   └── room.ts
│   ├── views/            # Pages
│   │   ├── Home.vue
│   │   └── Room.vue
│   ├── App.vue           # Composant racine
│   └── main.ts           # Point d'entrée
├── public/               # Fichiers statiques
├── index.html            # Page HTML principale
├── vite.config.ts        # Configuration Vite
├── tsconfig.json         # Configuration TypeScript
└── package.json          # Dépendances
```

## Installation

### Avec Docker (recommandé)

Le frontend est configuré pour fonctionner avec Docker. Utilisez la commande suivante depuis la racine du projet :

```bash
docker-compose up -d
```

### Sans Docker

1. Installez les dépendances :

```bash
npm install
```

2. Démarrez le serveur de développement :

```bash
npm run dev
```

## Fonctionnalités principales

- **Page d'accueil** : Rejoindre ou créer une salle
- **Page de salle** :
  - Chat textuel en temps réel
  - Lecteur audio synchronisé
  - File d'attente de musiques
  - Recherche et ajout de musiques
  - Upload de musiques via URL

## Variables d'environnement

Les variables d'environnement suivantes peuvent être configurées :

- `VITE_API_URL` : URL de l'API backend (par défaut : http://localhost:8000)
- `VITE_AUTH_URL` : URL du service d'authentification PHP (par défaut : http://localhost:8080)

## Technologies utilisées

- Vue.js 3 avec Composition API
- Pinia pour la gestion d'état
- Vue Router pour la navigation
- TailwindCSS pour les styles
- Howler.js pour la lecture audio
- Color Thief pour l'extraction des couleurs des covers
- WebSockets pour la communication en temps réel

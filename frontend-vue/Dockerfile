FROM node:18-alpine

WORKDIR /app

# Installer les dépendances
COPY package.json ./
RUN npm install

# Exposer le port
EXPOSE 3000

# Démarrer le serveur de développement
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"] 
#!/bin/sh

# Attendre que la base de données soit prête
echo "Attente de la disponibilité de MariaDB..."
until nc -z mariadb 3306; do
  echo "MariaDB n'est pas encore disponible - attente..."
  sleep 2
done
echo "MariaDB est disponible !"

# Démarrer l'application
echo "Démarrage de l'API FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --reload 
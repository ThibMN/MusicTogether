<?php
// Configuration de l'authentification
// Masquer les erreurs PHP à l'utilisateur final
error_reporting(0);
ini_set('display_errors', 0);


// URL de base de l'API FastAPI
define('API_URL', 'http://backend:8000/api');

// Configuration de la base de données (utiliser les mêmes paramètres que dans docker-compose.yml)
define('DB_HOST', 'mariadb');
define('DB_NAME', 'musicdb');
define('DB_USER', 'root');
define('DB_PASS', 'password');

// Durée de validité du token JWT en secondes (1 jour)
define('JWT_EXPIRATION', 86400);

// Clé secrète pour les JWT (à changer en production)
define('JWT_SECRET', 'musictogether_secret_key_change_in_prod');

// URL de redirection après connexion réussie
define('REDIRECT_URL', 'http://frontend:3000');
?> 
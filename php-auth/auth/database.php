<?php
// Connexion à la base de données

function getDbConnection() {
    try {
        $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME;
        $conn = new PDO($dsn, DB_USER, DB_PASS);
        $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        return $conn;
    } catch (PDOException $e) {
        echo "<p class='mb-2 text-red-500'>Erreur de connexion à la base de données: " . $e->getMessage() . "</p>";
        echo "<p class='mb-2'>DSN: mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . "</p>";
        echo "<p class='mb-2'>User: " . DB_USER . "</p>";
        // Ne pas afficher le mot de passe en production
        if (getenv('APP_ENV') !== 'production') {
            echo "<p class='mb-2'>Password: " . substr(DB_PASS, 0, 1) . '***' . "</p>";
        }
        die();
    }
}

// Initialisation de la base de données (tables nécessaires pour l'authentification)
function initDatabase() {
    try {
        $conn = getDbConnection();
        
        // On vérifie simplement que la table users existe déjà (créée par FastAPI)
        try {
            $sql = "SELECT 1 FROM users LIMIT 1";
            $conn->query($sql);
        } catch (PDOException $e) {
            echo "<p class='mb-2 text-red-500'>La table 'users' n'existe pas: " . $e->getMessage() . "</p>";
            echo "<p class='mb-2 text-yellow-400'>Tentative de création de la table 'users'...</p>";
            
            // Création de la table users si elle n'existe pas
            $sql = "CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME NULL
            )";
            $conn->exec($sql);
        }
    } catch (Exception $e) {
        echo "<p class='mb-2 text-red-500'>Erreur lors de l'initialisation de la base de données: " . $e->getMessage() . "</p>";
    }
}

// Initialiser la base de données
initDatabase();
?> 
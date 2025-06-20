<?php
// Router simple pour les pages d'authentification

// Vérification du chemin des fichiers
if (!file_exists('auth/config.php')) {
    echo "<p class='mb-2 text-red-500'>ERREUR: Fichier config.php non trouvé!</p>";
    echo "<p class='mb-2'>Chemin courant: " . getcwd() . "</p>";
    echo "<p class='mb-2'>Contenu du dossier auth:</p><pre>";
    if (is_dir('auth')) {
        print_r(scandir('auth'));
    } else {
        echo "Le dossier auth n'existe pas!";
    }
    echo "</pre>";
    die();
}

require_once 'auth/config.php';
require_once 'auth/database.php';

// Router basique
$action = $_GET['action'] ?? 'login';

switch ($action) {
    case 'login':
        if (file_exists('auth/login.php')) {
            require_once 'auth/login.php';
        } else {
            echo "<p class='text-red-500'>Fichier login.php non trouvé!</p>";
        }
        break;
    case 'register':
        if (file_exists('auth/register.php')) {
            require_once 'auth/register.php';
        } else {
            echo "<p class='text-red-500'>Fichier register.php non trouvé!</p>";
        }
        break;
    case 'logout':
        if (file_exists('auth/logout.php')) {
            require_once 'auth/logout.php';
        } else {
            echo "<p class='text-red-500'>Fichier logout.php non trouvé!</p>";
        }
        break;
    case 'process_login':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            if (file_exists('auth/process_login.php')) {
                require_once 'auth/process_login.php';
            } else {
                echo "<p class='text-red-500'>Fichier process_login.php non trouvé!</p>";
            }
        } else {
            header('Location: index.php?action=login');
        }
        break;
    case 'process_register':
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            if (file_exists('auth/process_register.php')) {
                require_once 'auth/process_register.php';
            } else {
                echo "<p class='text-red-500'>Fichier process_register.php non trouvé!</p>";
            }
        } else {
            header('Location: index.php?action=register');
        }
        break;
    default:
        if (file_exists('auth/login.php')) {
            require_once 'auth/login.php';
        } else {
            echo "<p class='text-red-500'>Fichier login.php non trouvé!</p>";
        }
}
?> 
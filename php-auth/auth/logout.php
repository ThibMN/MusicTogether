<?php
// Déconnexion de l'utilisateur

// Détruire la session
session_unset();
session_destroy();

// Rediriger vers la page de connexion
header('Location: index.php?action=login');
exit;
?> 
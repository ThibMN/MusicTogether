<?php
// Traitement du formulaire de connexion

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: index.php?action=login');
    exit;
}

// Récupérer les données du formulaire
$username = $_POST['username'] ?? '';
$password = $_POST['password'] ?? '';

// Validation basique
if (empty($username) || empty($password)) {
    $_SESSION['error'] = "Tous les champs sont obligatoires";
    header('Location: index.php?action=login');
    exit;
}

try {
    // Connexion à la base de données
    $conn = getDbConnection();

    // Recherche de l'utilisateur par nom d'utilisateur
    $stmt = $conn->prepare('SELECT id, username, email, password FROM users WHERE username = :username');
    $stmt->bindParam(':username', $username);
    $stmt->execute();

    $user = $stmt->fetch(PDO::FETCH_ASSOC);
    
    // Vérifier si l'utilisateur existe et le mot de passe est correct
    if (!$user) {
        $_SESSION['error'] = "Nom d'utilisateur ou mot de passe incorrect";
        header('Location: index.php?action=login');
        exit;
    }
    
    // Pour éviter les problèmes, vérifions si le mot de passe est déjà hashé
    // Si le mot de passe semble être un hash, on compare directement
    // sinon on utilise password_verify
    $passwordMatches = false;
    if (strlen($user['password']) > 30) {
        $passwordMatches = password_verify($password, $user['password']);
    } else {
        // Comparaison simple pour les tests (À ÉVITER EN PRODUCTION!)
        $passwordMatches = ($password === $user['password']);
    }
    
    if (!$passwordMatches) {
        $_SESSION['error'] = "Nom d'utilisateur ou mot de passe incorrect";
        header('Location: index.php?action=login');
        exit;
    }

    // Mettre à jour la dernière connexion
    $stmt = $conn->prepare('UPDATE users SET last_login = NOW() WHERE id = :id');
    $stmt->bindParam(':id', $user['id']);
    $stmt->execute();

    // Générer un token JWT pour l'API FastAPI
    $payload = [
        'user_id' => $user['id'],
        'username' => $user['username'],
        'email' => $user['email'],
        'exp' => time() + JWT_EXPIRATION
    ];

    // Dans un projet réel, utiliser une bibliothèque JWT appropriée
    // Ici on simule juste un token simple
    $token = base64_encode(json_encode($payload)) . '.' . hash_hmac('sha256', base64_encode(json_encode($payload)), JWT_SECRET);

    // Stocker les données utilisateur en session
    $_SESSION['user'] = [
        'id' => $user['id'],
        'username' => $user['username'],
        'email' => $user['email'],
        'token' => $token
    ];
    
    // Données utilisateur à envoyer à l'application Vue.js
    $userData = [
        'id' => $user['id'],
        'username' => $user['username'],
        'email' => $user['email'],
        'token' => $token
    ];
    
    // Afficher un message de succès et utiliser JavaScript pour la redirection
    // et communiquer avec l'application Vue.js
    header('Content-Type: text/html; charset=utf-8');
    ?>
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connexion réussie</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <script>
            // Cette fonction s'exécute immédiatement quand la page se charge
            (function() {
                var userData = <?= json_encode($userData) ?>;
                console.log("Authentification réussie:", userData);
                
                // Envoyer le message à la fenêtre parente
                function sendMessageToParent() {
                    try {
                        if (window.opener) {
                            window.opener.postMessage({
                                type: 'auth_success',
                                data: userData
                            }, '*');
                            console.log("Message envoyé à l'application principale");
                        } else {
                            console.error("window.opener n'existe pas");
                        }
                    } catch(e) {
                        console.error("Erreur lors de l'envoi du message", e);
                    }
                }
                
                // Envoyer le message toutes les 100ms pendant 1 seconde
                for (var i = 0; i < 10; i++) {
                    setTimeout(sendMessageToParent, i * 100);
                }
                
                // Fermer la fenêtre automatiquement après 1.5 secondes
                setTimeout(function() {
                    window.close();
                    // Si la fenêtre ne se ferme pas (ce qui est possible à cause des restrictions de navigateur),
                    // rediriger vers l'application principale
                    setTimeout(function() {
                        window.location.href = "http://localhost:3000";
                    }, 500);
                }, 1500);
            })();
        </script>
    </head>
    <body class="bg-gray-900 text-white flex items-center justify-center h-screen">
        <div class="bg-gray-800 p-8 rounded-lg shadow-lg text-center">
            <div class="text-green-500 text-2xl mb-4">Connexion réussie!</div>
            <div class="mb-4">Bonjour, <?= htmlspecialchars($user['username']) ?>!</div>
            <div class="text-gray-400">Redirection en cours...</div>
            <div class="mt-4">
                <div class="w-full bg-gray-700 rounded-full h-2.5 mb-4">
                    <div class="bg-blue-600 h-2.5 rounded-full w-full animate-pulse"></div>
                </div>
            </div>
            <button class="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded" 
                    onclick="window.close(); window.location.href = 'http://localhost:3000';">
                Cliquez ici si vous n'êtes pas redirigé automatiquement
            </button>
        </div>
    </body>
    </html>
    <?php
    exit;
} catch (PDOException $e) {
    $_SESSION['error'] = "Erreur de base de données: " . $e->getMessage();
    header('Location: index.php?action=login');
    exit;
}
?> 
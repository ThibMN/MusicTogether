<?php
// Traitement du formulaire d'inscription

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: index.php?action=register');
    exit;
}

// Récupérer les données du formulaire
$username = $_POST['username'] ?? '';
$email = $_POST['email'] ?? '';
$password = $_POST['password'] ?? '';
$confirm_password = $_POST['confirm_password'] ?? '';

// Validation basique
if (empty($username) || empty($email) || empty($password) || empty($confirm_password)) {
    $_SESSION['error'] = "Tous les champs sont obligatoires";
    header('Location: index.php?action=register');
    exit;
}

if ($password !== $confirm_password) {
    $_SESSION['error'] = "Les mots de passe ne correspondent pas";
    header('Location: index.php?action=register');
    exit;
}

if (strlen($password) < 6) {
    $_SESSION['error'] = "Le mot de passe doit contenir au moins 6 caractères";
    header('Location: index.php?action=register');
    exit;
}

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    $_SESSION['error'] = "Format d'email invalide";
    header('Location: index.php?action=register');
    exit;
}

try {
    // Connexion à la base de données
    $conn = getDbConnection();

    // Vérifier si l'utilisateur ou l'email existe déjà
    $stmt = $conn->prepare('SELECT id FROM users WHERE username = :username OR email = :email');
    $stmt->bindParam(':username', $username);
    $stmt->bindParam(':email', $email);
    $stmt->execute();

    if ($stmt->rowCount() > 0) {
        $_SESSION['error'] = "Ce nom d'utilisateur ou cet email est déjà utilisé";
        header('Location: index.php?action=register');
        exit;
    }

    // Hasher le mot de passe
    $hashed_password = password_hash($password, PASSWORD_DEFAULT);

    // Insérer le nouvel utilisateur
    $stmt = $conn->prepare('INSERT INTO users (username, email, password, created_at) VALUES (:username, :email, :password, NOW())');
    $stmt->bindParam(':username', $username);
    $stmt->bindParam(':email', $email);
    $stmt->bindParam(':password', $hashed_password);
    $stmt->execute();

    // Récupérer l'ID de l'utilisateur créé
    $user_id = $conn->lastInsertId();

    // Générer un token JWT pour l'API FastAPI
    $payload = [
        'user_id' => $user_id,
        'username' => $username,
        'email' => $email,
        'exp' => time() + JWT_EXPIRATION
    ];

    // Dans un projet réel, utiliser une bibliothèque JWT appropriée
    // Ici on simule juste un token simple
    $token = base64_encode(json_encode($payload)) . '.' . hash_hmac('sha256', base64_encode(json_encode($payload)), JWT_SECRET);

    // Stocker les données utilisateur en session
    $_SESSION['user'] = [
        'id' => $user_id,
        'username' => $username,
        'email' => $email,
        'token' => $token
    ];

    // Données utilisateur à envoyer à l'application Vue.js
    $userData = [
        'id' => $user_id,
        'username' => $username,
        'email' => $email,
        'token' => $token
    ];
    
    // Afficher un message de succès et utiliser JavaScript pour la redirection
    // et communiquer avec l'application Vue.js
    header('Content-Type: text/html; charset=utf-8');
    ?>
    <!DOCTYPE html>
    <html>
    <head>
        <title>Inscription réussie</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <script>
            // Cette fonction s'exécute immédiatement quand la page se charge
            (function() {
                var userData = <?= json_encode($userData) ?>;
                console.log("Inscription réussie:", userData);
                
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
            <div class="text-green-500 text-2xl mb-4">Inscription réussie!</div>
            <div class="mb-4">Bienvenue, <?= htmlspecialchars($username) ?>!</div>
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
    $_SESSION['error'] = "Erreur lors de l'inscription: " . $e->getMessage();
    header('Location: index.php?action=register');
    exit;
}
?> 
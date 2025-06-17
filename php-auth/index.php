<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MusicTogether - Authentification</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
    <div class="w-full max-w-md p-6 bg-gray-800 rounded-lg shadow-xl">
        <?php 
        // Debug
        echo "<p class='mb-4 text-green-500'>PHP fonctionne! Version: " . phpversion() . "</p>";
        
        // Inclure le router
        include 'auth/router.php'; 
        ?>
    </div>

    <!-- La fonction redirectToApp n'est plus nécessaire ici car elle est définie 
    directement dans les scripts de traitement process_login.php et process_register.php -->
</body>
</html> 
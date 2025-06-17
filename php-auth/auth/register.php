<?php 
// Si l'utilisateur est déjà connecté, le rediriger
if (isset($_SESSION['user'])) {
    header('Location: index.php?action=profile');
    exit;
}
?>

<div class="text-center mb-6">
    <h1 class="text-2xl font-bold">Inscription à MusicTogether</h1>
</div>

<?php if (isset($_SESSION['error'])): ?>
    <div class="bg-red-500 text-white p-3 mb-4 rounded">
        <?php echo $_SESSION['error']; unset($_SESSION['error']); ?>
    </div>
<?php endif; ?>

<form action="index.php?action=process_register" method="POST">
    <div class="mb-4">
        <label class="block text-sm font-medium mb-2" for="username">Nom d'utilisateur</label>
        <input type="text" id="username" name="username" required 
               class="w-full px-3 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    
    <div class="mb-4">
        <label class="block text-sm font-medium mb-2" for="email">Email</label>
        <input type="email" id="email" name="email" required 
               class="w-full px-3 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    
    <div class="mb-4">
        <label class="block text-sm font-medium mb-2" for="password">Mot de passe</label>
        <input type="password" id="password" name="password" required 
               class="w-full px-3 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    
    <div class="mb-6">
        <label class="block text-sm font-medium mb-2" for="confirm_password">Confirmer le mot de passe</label>
        <input type="password" id="confirm_password" name="confirm_password" required 
               class="w-full px-3 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-blue-500">
    </div>
    
    <div class="flex flex-col gap-4">
        <button type="submit" 
                class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            S'inscrire
        </button>
        
        <a href="index.php?action=login" 
           class="text-center text-blue-400 hover:text-blue-300">
            Déjà un compte ? Se connecter
        </a>
    </div>
</form> 
<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();
const roomCode = ref('');
const error = ref('');
const username = ref('');

// Message de bienvenue personnalisé en fonction de l'état d'authentification
const welcomeMessage = computed(() => {
  return authStore.isAuthenticated && authStore.user
    ? `Bienvenue ${authStore.user.username} ! Prêt à écouter de la musique ?`
    : 'Rejoignez dès maintenant une salle MusicTogether en entrant son code';
});

// Fonction pour rejoindre une salle existante ou en créer une nouvelle
const joinRoom = async () => {
  if (!roomCode.value) {
    error.value = 'Veuillez entrer un code de salle';
    return;
  }
  
  // Redirection vers la salle
  router.push(`/room/${roomCode.value.toUpperCase()}`);
};

const handleAuth = () => {
  if (authStore.isAuthenticated) {
    // Si déjà connecté, se déconnecter
    authStore.logout();
    console.log('Déconnexion effectuée');
  } else {
    // Ouvrir la fenêtre d'authentification
    authStore.openAuthWindow();
  }
};

// Forcer le rafraîchissement du nom d'utilisateur quand l'état d'authentification change
watch(() => authStore.isAuthenticated, (newVal) => {
  if (newVal && authStore.user) {
    username.value = authStore.user.username;
    console.log('État d\'authentification mis à jour, username:', username.value);
  } else {
    username.value = '';
  }
}, { immediate: true });

// Vérifier l'authentification au démarrage et à chaque fois que le composant est monté
onMounted(async () => {
  await authStore.validateToken();
  if (authStore.user) {
    username.value = authStore.user.username;
  }
  
  // Debug
  console.log('Home component loaded, auth state:', 
    authStore.isAuthenticated ? `authenticated as ${username.value}` : 'not authenticated');
});
</script>

<template>
  <div class="h-screen w-screen flex items-center justify-center bg-gray-900">
    <div class="bg-gray-800 p-10 rounded-lg shadow-lg text-center max-w-md w-full">
      <div class="flex justify-end mb-4">
        <button 
          @click="handleAuth"
          :class="[
            'px-4 py-1 rounded-full text-sm transition-colors',
            authStore.isAuthenticated 
              ? 'bg-red-600 hover:bg-red-700 text-white' 
              : 'bg-green-600 hover:bg-green-700 text-white'
          ]"
        >
          {{ authStore.isAuthenticated ? 'Se déconnecter' : 'Se connecter' }}
        </button>
      </div>
      
      <h1 class="text-4xl font-bold text-white mb-8">MusicTogether</h1>
      
      <div v-if="authStore.isAuthenticated" class="mb-4 text-green-400">
        Connecté en tant que <span class="font-bold">{{ username }}</span>
      </div>
      
      <div class="mb-8">
        <h2 class="text-xl text-white mb-4">{{ welcomeMessage }}</h2>
        
        <div class="mb-4">
          <input 
            v-model="roomCode"
            type="text" 
            placeholder="Code de salle (ex: ABCD)"
            class="w-full p-3 rounded text-center text-black"
            @keyup.enter="joinRoom"
          />
        </div>
        
        <p class="text-sm text-white">
          Si la salle n'existe pas, elle sera créée pour vous
        </p>
        
        <p v-if="error" class="text-red-500 mt-2">{{ error }}</p>
      </div>
      
      <button 
        @click="joinRoom"
        class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full w-full"
      >
        Rejoindre la salle
      </button>
    </div>
  </div>
</template> 
<script setup lang="ts">
// App.vue est maintenant un conteneur pour les routes
import { onMounted } from 'vue';
import { useAuthStore } from './stores/auth';

// Store d'authentification
const authStore = useAuthStore();

// Vérifier l'authentification au chargement
onMounted(async () => {
  console.log('App mounted, checking authentication');
  
  try {
    const isValid = await authStore.validateToken();
    console.log('Token validation result:', isValid);
    
    if (isValid && authStore.user) {
      console.log('User is authenticated:', authStore.user.username);
    } else {
      console.log('No valid authentication found');
    }
  } catch (error) {
    console.error('Error validating authentication:', error);
  }
  
  // Intercepter les erreurs non capturées
  window.addEventListener('error', (event) => {
    console.error('Uncaught error:', event.error);
  });
  
  // Intercepter les rejets de promesses non gérés
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
  });
});
</script>

<template>
  <div class="h-screen w-screen bg-gray-900 text-white flex flex-col">
    <router-view />
  </div>
</template>

<style>
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  background-color: #121212;
  color: #ffffff;
}

#app {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Styles pour les scrollbars */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>

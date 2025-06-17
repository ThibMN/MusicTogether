<template>
  <div class="flex flex-col h-screen w-screen bg-gray-900">
    <!-- Message d'erreur -->
    <div v-if="error" class="bg-red-600 text-white p-4 text-center">
      {{ error }}
    </div>
    
    <!-- Header avec titre et bouton quitter -->
    <header class="bg-gray-800 p-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center">
          <h1 class="text-xl font-bold text-white">MusicTogether</h1>
          <span class="ml-4 bg-blue-600 px-3 py-1 rounded-full text-sm">
            Room: {{ roomCode }}
          </span>
        </div>
        
        <button @click="leaveRoom" class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded">
          Quitter
        </button>
      </div>
    </header>
    
    <!-- Barre de recherche (séparée du header pour être plus visible) -->
    <div class="bg-gray-800 p-4 border-t border-gray-700 shadow-md">
      <SearchBar />
    </div>
    
    <!-- Contenu principal -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Chat (panneau gauche) -->
      <div class="w-1/4 bg-gray-800 p-4 flex flex-col">
        <h2 class="text-lg font-bold mb-4">Chat</h2>
        
        <div class="flex-grow overflow-y-auto mb-4">
          <div v-for="(message, index) in chatMessages" :key="index" class="mb-2">
            <span class="font-bold" :style="{ color: message.color }">{{ message.username }}:</span>
            <span class="text-white">{{ message.text }}</span>
          </div>
        </div>
        
        <div class="flex">
          <input 
            v-model="chatInput" 
            type="text" 
            placeholder="Envoyer un message..." 
            class="flex-grow p-2 rounded-l bg-gray-700 text-white"
            @keyup.enter="sendChatMessage"
          />
          <button 
            @click="sendChatMessage" 
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-r"
          >
            Envoyer
          </button>
        </div>
      </div>
      
      <!-- Lecteur (centre) -->
      <div class="flex-grow relative bg-gray-900">
        <!-- Contenu du lecteur -->
        <div class="relative z-10 h-full">
          <MusicPlayer />
        </div>
      </div>
      
      <!-- File d'attente (panneau droit) -->
      <div class="w-1/4 bg-gray-800">
        <QueuePanel />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useRoomStore } from '../stores/room';
import { useMusicStore } from '../stores/music';
import { useQueueStore } from '../stores/queue';
import SearchBar from '../components/SearchBar.vue';
import MusicPlayer from '../components/MusicPlayer.vue';
import QueuePanel from '../components/QueuePanel.vue';

const route = useRoute();
const router = useRouter();
const roomStore = useRoomStore();
const musicStore = useMusicStore();
const queueStore = useQueueStore();

// Récupérer le code de la salle depuis l'URL
const roomCode = ref(route.params.roomCode);
const error = ref('');
const connectionCheckInterval = ref(null);
const maxReconnectAttempts = 5;
const reconnectAttempts = ref(0);
const isConnecting = ref(false);

// État du chat
const chatInput = ref('');
const chatMessages = ref([
  { username: 'Système', text: ' Bienvenue dans la salle ' + roomCode.value, color: '#1db954' }
]);

// Vérifier périodiquement l'état de la connexion WebSocket
const startConnectionCheck = () => {
  connectionCheckInterval.value = setInterval(() => {
    if (!roomStore.isConnected && roomStore.currentRoom && !isConnecting.value) {
      console.log('Détection de déconnexion WebSocket, tentative de reconnexion...');
      error.value = 'Connexion perdue. Tentative de reconnexion...';
      
      // Tenter de se reconnecter à la salle (max 5 tentatives)
      if (reconnectAttempts.value < maxReconnectAttempts) {
        reconnectAttempts.value++;
        isConnecting.value = true;
        roomStore.connectWebSocket(roomCode.value).finally(() => {
          isConnecting.value = false;
        });
      } else {
        error.value = 'Impossible de se reconnecter après plusieurs tentatives. Veuillez rafraîchir la page.';
        clearInterval(connectionCheckInterval.value);
      }
    } else if (roomStore.isConnected && error.value.includes('Connexion perdue')) {
      // Effacer le message d'erreur si la connexion est rétablie
      error.value = '';
      reconnectAttempts.value = 0;
    }
  }, 5000); // Vérifier toutes les 5 secondes
};

// Fonction pour rejoindre la salle
onMounted(async () => {
  console.log('Room component mounted, roomCode:', roomCode.value);
  
  try {
    console.log('Tentative de rejoindre la salle via le store...');
    isConnecting.value = true;
    await roomStore.joinRoom(roomCode.value);
    isConnecting.value = false;
    console.log('Salle rejointe avec succès:', roomStore.currentRoom);
    
    // Charger la file d'attente
    if (roomStore.currentRoom) {
      await queueStore.loadQueue(roomStore.currentRoom.id);
    }
    
    // Vérifier que la connexion WebSocket est bien établie
    if (!roomStore.isConnected) {
      console.error('La connexion WebSocket n\'a pas été établie correctement');
      error.value = 'Impossible de se connecter à la salle. Tentative de reconnexion...';
      
      // Tenter une nouvelle connexion après 2 secondes
      setTimeout(async () => {
        if (!roomStore.isConnected && !isConnecting.value) {
          reconnectAttempts.value++;
          isConnecting.value = true;
          
          try {
            console.log('Tentative de reconnexion à la salle...');
            roomStore.connectWebSocket(roomCode.value);
            
            // Attendre que la connexion soit établie
            setTimeout(() => {
              isConnecting.value = false;
              if (roomStore.isConnected) {
                error.value = '';
                reconnectAttempts.value = 0;
              } else if (reconnectAttempts.value < maxReconnectAttempts) {
                // On lance une autre tentative plus tard via le connectionCheck
                error.value = 'Reconnexion en cours...';
              } else {
                error.value = 'Échec des tentatives de connexion. Veuillez réessayer plus tard.';
              }
            }, 3000);
          } catch (e) {
            isConnecting.value = false;
            console.error('Erreur lors de la reconnexion:', e);
          }
        }
      }, 2000);
    }
    
    // Démarrer la vérification périodique de la connexion
    startConnectionCheck();
    
  } catch (error) {
    isConnecting.value = false;
    console.error('Erreur détaillée lors de la connexion à la salle:', error);
    
    // Afficher un message d'erreur avant la redirection
    error.value = 'Erreur lors de la connexion à la salle: ' + (error.message || 'Erreur inconnue');
    
    // On ne redirige pas automatiquement pour laisser l'utilisateur lire le message
  }
});

// Fonction pour quitter la salle
const leaveRoom = () => {
  roomStore.leaveRoom();
  router.push('/');
};

// Fonction pour envoyer un message dans le chat
const sendChatMessage = () => {
  if (!chatInput.value.trim()) return;
  
  const message = {
    username: 'Vous',
    text: ' ' + chatInput.value,
    color: '#3b82f6'
  };
  
  chatMessages.value.push(message);
  chatInput.value = '';
};

// Nettoyer avant de quitter la page
onBeforeUnmount(() => {
  roomStore.leaveRoom();
  
  // Arrêter la vérification périodique de la connexion
  if (connectionCheckInterval.value) {
    clearInterval(connectionCheckInterval.value);
  }
});
</script>

<style scoped>
/* Pas de styles spécifiques nécessaires */
</style> 
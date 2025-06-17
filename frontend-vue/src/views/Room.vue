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
      <div class="flex-grow relative">
        <!-- Visualizer en arrière-plan -->
        <div ref="visualizerContainer" class="absolute inset-0 z-0" id="visualizer"></div>
        
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
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useRoomStore } from '../stores/room';
import { useMusicStore } from '../stores/music';
import { useQueueStore } from '../stores/queue';
import SearchBar from '../components/SearchBar.vue';
import MusicPlayer from '../components/MusicPlayer.vue';
import QueuePanel from '../components/QueuePanel.vue';

// Essayer d'importer Butterchurn si disponible
let butterchurn = null;
try {
  butterchurn = require('butterchurn');
} catch (e) {
  console.warn('Butterchurn non disponible:', e);
}

const route = useRoute();
const router = useRouter();
const roomStore = useRoomStore();
const musicStore = useMusicStore();
const queueStore = useQueueStore();

// Récupérer le code de la salle depuis l'URL
const roomCode = ref(route.params.roomCode);
const error = ref('');
const visualizerContainer = ref(null);
const visualizer = ref(null);
const audioContext = ref(null);
const audioAnalyser = ref(null);
const connectionCheckInterval = ref(null);

// État du chat
const chatInput = ref('');
const chatMessages = ref([
  { username: 'Système', text: ' Bienvenue dans la salle ' + roomCode.value, color: '#1db954' }
]);

// Vérifier périodiquement l'état de la connexion WebSocket
const startConnectionCheck = () => {
  connectionCheckInterval.value = setInterval(() => {
    if (!roomStore.isConnected && roomStore.currentRoom) {
      console.log('Détection de déconnexion WebSocket, tentative de reconnexion...');
      error.value = 'Connexion perdue. Tentative de reconnexion...';
      
      // Tenter de se reconnecter à la salle (max 5 tentatives)
      if (roomStore.reconnectAttempts < 5) {
        roomStore.connectWebSocket(roomCode.value);
      } else {
        error.value = 'Impossible de se reconnecter après plusieurs tentatives. Veuillez rafraîchir la page.';
        clearInterval(connectionCheckInterval.value);
      }
    } else if (roomStore.isConnected && error.value.includes('Connexion perdue')) {
      // Effacer le message d'erreur si la connexion est rétablie
      error.value = '';
    }
  }, 5000); // Vérifier toutes les 5 secondes
};

// Fonction pour rejoindre la salle
onMounted(async () => {
  console.log('Room component mounted, roomCode:', roomCode.value);
  
  try {
    console.log('Tentative de rejoindre la salle via le store...');
    await roomStore.joinRoom(roomCode.value);
    console.log('Salle rejointe avec succès:', roomStore.currentRoom);
    
    // Charger la file d'attente
    if (roomStore.currentRoom) {
      await queueStore.loadQueue(roomStore.currentRoom.id);
    }
    
    // Initialiser le visualiseur si Butterchurn est disponible
    initVisualizer();
    
    // Vérifier que la connexion WebSocket est bien établie
    if (!roomStore.isConnected) {
      console.error('La connexion WebSocket n\'a pas été établie correctement');
      error.value = 'Impossible de se connecter à la salle. Tentative de reconnexion...';
      
      // On attend un peu pour voir si la connexion s'établit
      setTimeout(() => {
        if (!roomStore.isConnected) {
          console.error('Échec de la connexion WebSocket après délai');
          error.value = 'Échec de la connexion. Tentative de reconnexion...';
          
          // Tenter de se reconnecter à la salle
          roomStore.connectWebSocket(roomCode.value);
          
          // Attendre encore un peu pour voir si la reconnexion fonctionne
          setTimeout(() => {
            if (!roomStore.isConnected) {
              error.value = 'Échec de la reconnexion. Retour à l\'accueil...';
              setTimeout(() => {
                router.push('/');
              }, 2000);
            } else {
              error.value = '';
            }
          }, 5000);
        } else {
          error.value = '';
        }
      }, 5000);
    }
    
    // Démarrer la vérification périodique de la connexion
    startConnectionCheck();
    
  } catch (error) {
    console.error('Erreur détaillée lors de la connexion à la salle:', error);
    
    // Afficher un message d'erreur avant la redirection
    error.value = 'Erreur lors de la connexion à la salle: ' + (error.message || 'Erreur inconnue');
    
    setTimeout(() => {
      router.push('/');
    }, 3000);
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

// Initialiser le visualiseur audio avec Butterchurn
const initVisualizer = () => {
  if (!butterchurn || !visualizerContainer.value) return;
  
  try {
    // Créer un contexte audio
    audioContext.value = new (window.AudioContext || window.webkitAudioContext)();
    
    // Créer un analyseur audio
    audioAnalyser.value = audioContext.value.createAnalyser();
    audioAnalyser.value.fftSize = 2048;
    
    // Créer un visualiseur Butterchurn
    visualizer.value = butterchurn.createVisualizer(
      audioContext.value,
      visualizerContainer.value,
      {
        width: visualizerContainer.value.clientWidth,
        height: visualizerContainer.value.clientHeight
      }
    );
    
    // Connecter l'analyseur au visualiseur
    visualizer.value.connectAudio(audioAnalyser.value);
    
    // Démarrer le rendu
    visualizer.value.setRendererSize(
      visualizerContainer.value.clientWidth,
      visualizerContainer.value.clientHeight
    );
    
    // Charger un preset par défaut
    const defaultPreset = {
      name: 'Default Preset',
      // Un preset très simple
      waves: [],
      init_eqs: [],
      init_code: '',
      per_frame_code: '',
      per_pixel_code: '',
      warp: 1.0,
      zoom: 1.0,
      rot: 0.0,
      cx: 0.5,
      cy: 0.5,
      dx: 0.0,
      dy: 0.0
    };
    
    visualizer.value.loadPreset(defaultPreset, 0.0);
    
    // Démarrer la boucle de rendu
    renderVisualizer();
    
    // Ajuster la taille lors du redimensionnement de la fenêtre
    window.addEventListener('resize', resizeVisualizer);
  } catch (error) {
    console.error('Erreur lors de l\'initialisation du visualiseur:', error);
  }
};

// Fonction de rendu du visualiseur
const renderVisualizer = () => {
  if (visualizer.value) {
    visualizer.value.render();
    requestAnimationFrame(renderVisualizer);
  }
};

// Redimensionner le visualiseur
const resizeVisualizer = () => {
  if (visualizer.value && visualizerContainer.value) {
    visualizer.value.setRendererSize(
      visualizerContainer.value.clientWidth,
      visualizerContainer.value.clientHeight
    );
  }
};

// Nettoyer avant de quitter la page
onBeforeUnmount(() => {
  roomStore.leaveRoom();
  
  // Arrêter la vérification périodique de la connexion
  if (connectionCheckInterval.value) {
    clearInterval(connectionCheckInterval.value);
  }
  
  // Nettoyer le visualiseur
  if (visualizer.value) {
    visualizer.value = null;
  }
  
  // Nettoyer le contexte audio
  if (audioContext.value) {
    audioContext.value.close();
  }
  
  // Supprimer l'écouteur d'événements de redimensionnement
  window.removeEventListener('resize', resizeVisualizer);
});
</script>

<style scoped>
/* Styles pour le visualiseur */
#visualizer {
  background-color: #000;
  opacity: 0.6;
}
</style> 
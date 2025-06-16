<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import ChatPanel from '../components/ChatPanel.vue';
import MusicPlayer from '../components/MusicPlayer.vue';
import QueuePanel from '../components/QueuePanel.vue';
import SearchBar from '../components/SearchBar.vue';
import { useRoomStore } from '../stores/room';
import { useMusicStore } from '../stores/music';
import { useChatStore } from '../stores/chat';
import { useQueueStore } from '../stores/queue';

const route = useRoute();
const roomCode = ref(route.params.roomCode as string);
const roomStore = useRoomStore();
const musicStore = useMusicStore();
const chatStore = useChatStore();
const queueStore = useQueueStore();

// Initialisation de la salle
onMounted(async () => {
  // Connexion à la salle
  await roomStore.joinRoom(roomCode.value);
  
  // Chargement des données initiales
  await Promise.all([
    chatStore.loadMessages(roomStore.currentRoom?.id),
    queueStore.loadQueue(roomStore.currentRoom?.id)
  ]);
});

// Déconnexion de la salle
onUnmounted(() => {
  roomStore.leaveRoom();
});

// Surveillance des changements de paramètres de route
watch(() => route.params.roomCode, (newRoomCode) => {
  if (newRoomCode !== roomCode.value) {
    roomCode.value = newRoomCode as string;
    roomStore.leaveRoom();
    roomStore.joinRoom(roomCode.value);
  }
});
</script>

<template>
  <div class="h-screen w-screen bg-gray-900 text-white flex flex-col overflow-hidden">
    <!-- Barre de recherche -->
    <div class="bg-gray-800 p-4">
      <SearchBar />
    </div>
    
    <!-- Code de la salle -->
    <div class="bg-gray-800 text-center py-2 border-t border-gray-700">
      <span class="text-sm font-medium">Room: {{ roomCode }}</span>
    </div>
    
    <!-- Contenu principal -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Chat (panneau gauche) -->
      <div class="w-1/4 border-r border-gray-700 overflow-hidden">
        <ChatPanel />
      </div>
      
      <!-- Lecteur de musique (panneau central) -->
      <div class="w-2/4 flex flex-col items-center justify-center overflow-auto">
        <MusicPlayer />
      </div>
      
      <!-- File d'attente (panneau droit) -->
      <div class="w-1/4 border-l border-gray-700 overflow-hidden">
        <QueuePanel />
      </div>
    </div>
  </div>
</template> 
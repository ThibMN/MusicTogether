<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useChatStore } from '../stores/chat';
import { useRoomStore } from '../stores/room';
import { useAuthStore } from '../stores/auth';

// Stores
const chatStore = useChatStore();
const roomStore = useRoomStore();
const authStore = useAuthStore();

// État local
const newMessage = ref('');
const messageContainer = ref<HTMLElement | null>(null);
const errorMessage = ref('');

// Messages
const messages = computed(() => chatStore.messages);

// Nom d'utilisateur
const username = computed(() => authStore.user?.username || 'Anonyme');

// Envoyer un message
const sendMessage = async () => {
  if (!newMessage.value.trim() || !roomStore.currentRoom) return;
  
  console.log('Tentative d\'envoi de message:', newMessage.value);
  console.log('Room ID:', roomStore.currentRoom.id);
  console.log('User ID:', authStore.user?.id);
  
  errorMessage.value = '';
  
  // Vérifier si l'utilisateur est connecté
  if (!authStore.isAuthenticated) {
    errorMessage.value = 'Vous devez être connecté pour envoyer des messages';
    return;
  }
  
  try {
    const payload = {
      room_id: roomStore.currentRoom.id,
      message: newMessage.value
    };
    console.log('Payload envoyé:', payload);
    
    await chatStore.sendMessage(payload);
    
    // Ajouter le message localement pour une UI réactive immédiate
    const tempMessage = {
      id: 'local-' + Date.now(),
      username: username.value,
      message: newMessage.value,
      color: '#3b82f6', // Le message sera correctement coloré lors de la réception via WebSocket
      sent_at: new Date().toISOString()
    };
    
    chatStore.addMessage(tempMessage);
    console.log('Message local ajouté:', tempMessage);
    
    // Vider le champ de saisie
    newMessage.value = '';
  } catch (error) {
    console.error('Erreur lors de l\'envoi du message:', error);
    errorMessage.value = 'Erreur lors de l\'envoi du message. Veuillez réessayer.';
  }
};

// Faire défiler vers le bas
const scrollToBottom = async () => {
  await nextTick();
  if (messageContainer.value) {
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight;
  }
};

// Surveiller les nouveaux messages pour faire défiler
watch(() => messages.value.length, () => {
  scrollToBottom();
});

// Écouter les messages WebSocket
onMounted(() => {
  console.log('ChatPanel monté, écoute des WebSockets');
  
  // S'abonner aux mises à jour WebSocket pour les messages de chat
  roomStore.onPlaybackUpdate((data: any) => {
    console.log('Message WebSocket reçu dans ChatPanel:', data);
    
    if (data.type === 'chat_message' && data.message) {
      console.log('Message de chat reçu:', data.message);
      
      chatStore.addMessage({
        ...data.message,
        color: hashColor(data.message.username)
      });
      scrollToBottom();
    }
  });
  
  // Message de bienvenue système
  chatStore.addMessage({
    id: 'welcome-' + Date.now(),
    username: 'Système',
    message: `Bienvenue dans la salle ${roomStore.currentRoom?.room_code || ''}`,
    color: '#1db954',
    sent_at: new Date().toISOString()
  });
  
  // Faire défiler initialement
  scrollToBottom();
});

// Fonction pour générer une couleur à partir d'un nom d'utilisateur
function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // Générer une couleur pastel claire
  const h = Math.abs(hash) % 360;
  const s = 70 + Math.abs(hash) % 30; // 70-100%
  const l = 60 + Math.abs(hash) % 20; // 60-80%
  
  return `hsl(${h}, ${s}%, ${l}%)`;
}
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="p-3 border-b border-gray-700">
      <h2 class="text-lg font-semibold">Chat</h2>
    </div>
    
    <!-- Messages -->
    <div 
      ref="messageContainer"
      class="flex-1 overflow-y-auto p-4 space-y-2"
    >
      <div v-if="messages.length === 0" class="text-center text-gray-500">
        <p>Pas encore de messages</p>
        <p class="text-sm mt-2">Soyez le premier à écrire !</p>
      </div>
      
      <div 
        v-for="message in messages" 
        :key="message.id"
        class="break-words"
      >
        <span class="font-medium" :style="{ color: message.color || '#3b82f6' }">
          {{ message.username || 'Anonyme' }}:
        </span>
        <span class="ml-2 text-white">{{ message.message }}</span>
      </div>
      
      <!-- Message d'erreur -->
      <div v-if="errorMessage" class="bg-red-600/30 p-2 rounded text-sm text-white">
        {{ errorMessage }}
      </div>
    </div>
    
    <!-- Zone de saisie -->
    <div class="p-3 border-t border-gray-700">
      <div class="flex">
        <input
          v-model="newMessage"
          type="text"
          placeholder="Écrire un message..."
          maxlength="200"
          class="flex-1 p-2 rounded-l bg-gray-700 text-white focus:outline-none"
          @keyup.enter="sendMessage"
        />
        <button
          @click="sendMessage"
          class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-r"
        >
          Envoyer
        </button>
      </div>
    </div>
  </div>
</template> 
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useChatStore } from '../stores/chat';
import { useRoomStore } from '../stores/room';

// Stores
const chatStore = useChatStore();
const roomStore = useRoomStore();

// État local
const newMessage = ref('');
const messageContainer = ref<HTMLElement | null>(null);

// Messages
const messages = computed(() => chatStore.messages);

// Envoyer un message
const sendMessage = async () => {
  if (!newMessage.value.trim() || !roomStore.currentRoom) return;
  
  await chatStore.sendMessage({
    room_id: roomStore.currentRoom.id,
    content: newMessage.value
  });
  
  newMessage.value = '';
};

// Faire défiler vers le bas
const scrollToBottom = () => {
  if (messageContainer.value) {
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight;
  }
};

// Surveiller les nouveaux messages
watch(() => messages.value.length, () => {
  scrollToBottom();
});

// Initialisation
onMounted(() => {
  scrollToBottom();
});
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="p-3 border-b border-gray-700">
      <h2 class="text-lg font-semibold">Chat</h2>
    </div>
    
    <!-- Messages -->
    <div 
      ref="messageContainer"
      class="flex-1 overflow-y-auto p-4 space-y-4"
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
        <span class="ml-2">{{ message.content }}</span>
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

<script lang="ts">
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
  
  return `hsl(${h}, ${s}%, ${l}%)`.replace('#', '');
}
</script> 
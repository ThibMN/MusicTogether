<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onUnmounted, reactive } from 'vue';
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
const isConnected = ref(true);
const reconnectingChat = ref(false);
const messagesList = ref<any[]>([...chatStore.messages]); // Copie locale des messages
let messageCheckInterval: ReturnType<typeof setInterval> | null = null; // Variable pour l'intervalle de vérification

// Messages avec réactivité forcée
// const localMessages = reactive<any[]>([]);
// Utiliser localMessages au lieu de messages du store directement
const messages = computed(() => messagesList.value);

// Nom d'utilisateur
const username = computed(() => authStore.user?.username || 'Anonyme');

// Observer les changements du store et mettre à jour localMessages
watch(() => chatStore.messages, (newMessages) => {
  console.log('Changements détectés dans les messages du store:', newMessages.length);
  messagesList.value = [...newMessages]; // Créer une nouvelle référence
  nextTick(() => scrollToBottom());
}, { deep: true });

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
  
  // Vérifier si le WebSocket est connecté
  if (!roomStore.isConnected) {
    errorMessage.value = 'Impossible d\'envoyer des messages: déconnecté';
    // Tenter une reconnexion
    attemptChatReconnect();
    return;
  }
  
  // Sauvegarder le message à envoyer
  const messageToSend = newMessage.value;
  
  // Ajouter le message localement pour une UI réactive immédiate
  const tempId = 'local-' + Date.now();
  const tempMessage = {
    id: tempId,
    username: username.value,
    message: messageToSend,
    color: '#3b82f6', // Le message sera correctement coloré lors de la réception via WebSocket
    sent_at: new Date().toISOString()
  };
  
  chatStore.addMessage(tempMessage);
  console.log('Message local ajouté:', tempMessage);
  
  // Vider le champ de saisie immédiatement
  newMessage.value = '';
  
  try {
    const payload = {
      room_id: roomStore.currentRoom.id,
      message: messageToSend
    };
    console.log('Payload envoyé:', payload);
    
    // Ajouter un timer pour vérifier si le message reste bloqué en statut "envoi..."
    const confirmationTimeout = setTimeout(() => {
      // Vérifier si le message est toujours en attente
      const pendingMsgIndex = messagesList.value.findIndex(
        m => m.id === tempId
      );
      
      if (pendingMsgIndex !== -1) {
        console.log('Message toujours en attente après délai, conversion en confirmé');
        // Convertir en message confirmé pour éviter qu'il reste bloqué
        messagesList.value[pendingMsgIndex] = {
          ...messagesList.value[pendingMsgIndex],
          id: Date.now() // Un ID numérique pour simuler un ID de serveur
        };
      }
    }, 5000); // 5 secondes de timeout
    
    // Envoyer le message au serveur
    const response = await chatStore.sendMessage(payload);
    console.log('Message envoyé avec succès, ID serveur:', response.id);
    
    // Annuler le timer si la réponse est reçue normalement
    clearTimeout(confirmationTimeout);
    
  } catch (error) {
    console.error('Erreur lors de l\'envoi du message:', error);
    errorMessage.value = error instanceof Error ? error.message : 'Erreur lors de l\'envoi du message. Veuillez réessayer.';
    
    // Marquer le message comme échoué
    const failedMessageIndex = messagesList.value.findIndex(
      m => m.id === tempId
    );
    
    if (failedMessageIndex !== -1) {
      // Mettre à jour le message pour indiquer l'échec
      messagesList.value[failedMessageIndex] = {
        ...messagesList.value[failedMessageIndex],
        id: 'failed-' + tempId.substring(6), // Remplacer 'local-' par 'failed-'
        color: '#ff4d4d' // Rouge pour indiquer l'échec
      };
    }
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

// Fonction pour tenter de reconnecter le chat
const attemptChatReconnect = async () => {
  if (reconnectingChat.value || !roomStore.currentRoom) return;
  
  reconnectingChat.value = true;
  errorMessage.value = 'Connexion perdue, tentative de reconnexion...';
  
  try {
    // Réutiliser la méthode de reconnexion du RoomStore
    await roomStore.connectWebSocket(roomStore.currentRoom.room_code);
    errorMessage.value = '';
    isConnected.value = true;
  } catch (error) {
    console.error('Erreur de reconnexion du chat:', error);
    errorMessage.value = 'Impossible de se reconnecter. Veuillez actualiser la page.';
  } finally {
    reconnectingChat.value = false;
  }
};

// Surveillez l'état de connexion WebSocket
watch(() => roomStore.isConnected, (newValue) => {
  isConnected.value = newValue;
  
  if (!newValue) {
    errorMessage.value = 'Connexion perdue, tentative de reconnexion...';
    attemptChatReconnect();
  } else {
    errorMessage.value = '';
  }
});

// Écouter l'événement global de nouveau message
const handleNewChatMessage = (event: CustomEvent) => {
  console.log('Nouvel événement de message global reçu:', event.detail);
  scrollToBottom();
};

// Écouter les messages WebSocket
onMounted(() => {
  console.log('ChatPanel monté, écoute des WebSockets');
  
  // Message de bienvenue système
  chatStore.addMessage({
    id: 'welcome-' + Date.now(),
    username: 'Système',
    message: `Bienvenue dans la salle ${roomStore.currentRoom?.room_code || ''}`,
    color: '#1db954',
    sent_at: new Date().toISOString()
  });
  
  // S'abonner aux mises à jour WebSocket pour les messages de chat
  const chatMessageCallback = (data: any) => {
    console.log('Message WebSocket reçu dans ChatPanel:', data);
    
    if (data.type === 'chat_message' && data.message) {
      console.log('Message de chat reçu:', data.message);
      
      // Ajouter le message au store
      chatStore.addMessage({
        ...data.message,
        color: hashColor(data.message.username)
      });
      
      // Forcer un rafraîchissement visuel
      setTimeout(() => {
        if (messageContainer.value) {
          scrollToBottom();
        }
      }, 50);
    }
  };
  
  // Utiliser le nouveau système dédié aux messages de chat
  roomStore.onChatMessage(chatMessageCallback);
  
  // Écouter l'événement global pour les nouveaux messages
  window.addEventListener('new-chat-message', handleNewChatMessage as EventListener);
  
  // Faire défiler initialement
  scrollToBottom();
  
  // Vérifier l'état de connexion initial
  isConnected.value = roomStore.isConnected;
  if (!isConnected.value) {
    errorMessage.value = 'Connexion en cours...';
  }
  
  // Intervalle de rafraîchissement automatique
  messageCheckInterval = setInterval(async () => {
    await refreshMessages();
  }, 500);
  
  // Nettoyer l'intervalle lorsque le composant est démonté
  onUnmounted(() => {
    console.log('ChatPanel démonté, nettoyage des listeners');
    
    // Supprimer l'écouteur d'événements global
    window.removeEventListener('new-chat-message', handleNewChatMessage as EventListener);
    
    // Supprimer les callbacks du store
    // Comme les callbacks sont stockés par référence, on ne peut pas les supprimer facilement
    // Une solution alternative serait de modifier le RoomStore pour pouvoir supprimer des callbacks
    
    // Supprimer l'intervalle de vérification
    if (messageCheckInterval !== null) {
      window.clearInterval(messageCheckInterval);
      messageCheckInterval = null;
    }
  });
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

// Fonction pour réessayer l'envoi d'un message ayant échoué
const resendFailedMessage = async (failedMessage: any) => {
  if (!failedMessage || !failedMessage.message || !roomStore.currentRoom) return;
  
  console.log('Tentative de renvoi du message:', failedMessage);
  
  // Récupérer l'ID original du message échoué (pour le retrouver dans la liste)
  const originalFailedId = failedMessage.id;
  
  // Vérifier si l'utilisateur est connecté
  if (!authStore.isAuthenticated) {
    errorMessage.value = 'Vous devez être connecté pour envoyer des messages';
    return;
  }
  
  // Vérifier si le WebSocket est connecté
  if (!roomStore.isConnected) {
    errorMessage.value = 'Impossible d\'envoyer des messages: déconnecté';
    // Tenter une reconnexion
    attemptChatReconnect();
    return;
  }
  
  // Convertir le message échoué en message "en cours d'envoi"
  const failedIndex = messagesList.value.findIndex(m => m.id === originalFailedId);
  if (failedIndex !== -1) {
    const newTempId = 'local-' + Date.now();
    messagesList.value[failedIndex] = {
      ...messagesList.value[failedIndex],
      id: newTempId,
      color: '#3b82f6' // Restaurer la couleur normale
    };
    
    try {
      const payload = {
        room_id: roomStore.currentRoom.id,
        message: failedMessage.message
      };
      console.log('Payload renvoyé:', payload);
      
      // Envoyer le message au serveur
      const response = await chatStore.sendMessage(payload);
      console.log('Message renvoyé avec succès, ID serveur:', response.id);
      
      // Le message temporaire sera mis à jour par le store chat
      
    } catch (error) {
      console.error('Erreur lors du renvoi du message:', error);
      errorMessage.value = error instanceof Error ? error.message : 'Erreur lors de l\'envoi du message. Veuillez réessayer.';
      
      // Remettre le message en état d'échec
      const retryFailedIndex = messagesList.value.findIndex(m => m.id === newTempId);
      if (retryFailedIndex !== -1) {
        messagesList.value[retryFailedIndex] = {
          ...messagesList.value[retryFailedIndex],
          id: 'failed-' + newTempId.substring(6), // Remplacer 'local-' par 'failed-'
          color: '#ff4d4d' // Rouge pour indiquer l'échec
        };
      }
    }
  }
};

// Fonction pour rafraîchir les messages
const refreshMessages = async () => {
  console.log('Rafraîchissement des messages...');
  
  if (!roomStore.currentRoom) {
    console.error('Impossible de rafraîchir les messages: pas de salle courante');
    return;
  }
  
  try {
    // Vérifier la connexion WebSocket
    if (!roomStore.isConnected) {
      console.log('Tentative de reconnexion WebSocket...');
      await roomStore.connectWebSocket(roomStore.currentRoom.room_code);
      console.log('Reconnexion WebSocket réussie:', roomStore.isConnected);
    }
    
    // Recharger les messages
    console.log('Rechargement des messages pour la salle', roomStore.currentRoom.id);
    await chatStore.loadMessages(roomStore.currentRoom.id);
    
    // Mettre à jour notre liste locale
    messagesList.value = [...chatStore.messages];
    
    // Faire défiler vers le bas
    nextTick(() => {
      scrollToBottom();
      errorMessage.value = '';
    });
    
    console.log('Messages rechargés avec succès:', chatStore.messages.length);
  } catch (error) {
    console.error('Erreur lors du rafraîchissement des messages:', error);
    errorMessage.value = 'Erreur lors du rafraîchissement des messages.';
  }
};
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="p-3 border-b border-gray-700 flex items-center justify-between">
      <h2 class="text-lg font-semibold">Chat</h2>
      <div class="flex items-center gap-2">
        <div v-if="!isConnected" class="text-red-500 text-sm flex items-center">
          <span class="animate-pulse mr-1">•</span> Déconnecté
        </div>
        <div v-else class="text-green-500 text-sm flex items-center">
          <span class="mr-1">•</span> Connecté
        </div>
      </div>
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
      
      <!-- Message key inclut l'index pour forcer la réactivité -->
      <div 
        v-for="(message, index) in messages" 
        :key="`${message.id || 'msg'}-${index}`"
        class="break-words mb-2"
        :class="{ 
          'opacity-70': message.id && typeof message.id === 'string' && message.id.startsWith('local-'),
          'bg-red-900/20 p-1 rounded': message.id && typeof message.id === 'string' && message.id.startsWith('failed-')
        }"
      >
        <span class="font-medium" :style="{ color: message.color || '#3b82f6' }">
          {{ message.username || 'Anonyme' }}:
        </span>
        <span class="ml-2 text-white">{{ message.message }}</span>
        <span 
          v-if="message.id && typeof message.id === 'string' && message.id.startsWith('local-')"
          class="text-xs text-gray-400 ml-1 animate-pulse"
          title="Message en cours d'envoi"
        >
          (envoi...)
        </span>
        <span 
          v-if="message.id && typeof message.id === 'string' && message.id.startsWith('failed-')"
          class="text-xs text-red-400 ml-1 cursor-pointer"
          title="Cliquez pour réessayer"
          @click="resendFailedMessage(message)"
        >
          (échec - cliquer pour réessayer)
        </span>
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
          :disabled="!isConnected || reconnectingChat"
        />
        <button
          @click="sendMessage"
          class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-r"
          :disabled="!isConnected || reconnectingChat"
        >
          Envoyer
        </button>
      </div>
    </div>
  </div>
</template> 
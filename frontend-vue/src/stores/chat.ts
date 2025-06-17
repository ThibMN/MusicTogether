import { defineStore } from 'pinia';
import axios from 'axios';
import { useRoomStore } from './room';
import { useAuthStore } from './auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as any[],
    isLoading: false
  }),
  
  actions: {
    // Charger les messages d'une salle
    async loadMessages(roomId: number | undefined) {
      if (!roomId) return;
      
      this.isLoading = true;
      try {
        const response = await axios.get(`${API_URL}/api/chat/room/${roomId}`);
        this.messages = response.data;
      } catch (error) {
        console.error('Erreur lors du chargement des messages:', error);
      } finally {
        this.isLoading = false;
      }
    },
    
    // Envoyer un message
    async sendMessage(data: { room_id: number, message: string }) {
      try {
        // Récupérer l'ID utilisateur depuis le store d'authentification
        const authStore = useAuthStore();
        const userId = authStore.user?.id;
        
        if (!userId) {
          console.warn("Tentative d'envoi de message sans être connecté");
          throw new Error("Vous devez être connecté pour envoyer des messages");
        }
        
        const response = await axios.post(`${API_URL}/api/chat/`, {
          ...data,
          user_id: userId
        });
        
        // Le message sera ajouté via WebSocket dans le store de la salle
        return response.data;
      } catch (error) {
        console.error('Erreur lors de l\'envoi du message:', error);
        throw error;
      }
    },
    
    // Ajouter un message reçu via WebSocket
    addMessage(message: any) {
      this.messages.push(message);
      
      // Limiter le nombre de messages (garder les 100 derniers)
      if (this.messages.length > 100) {
        this.messages = this.messages.slice(-100);
      }
    },
    
    // Effacer les messages
    clearMessages() {
      this.messages = [];
    }
  }
}); 
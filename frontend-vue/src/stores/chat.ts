import { defineStore } from 'pinia';
import axios from 'axios';
import { useRoomStore } from './room';

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
        // Récupérer l'ID utilisateur (à implémenter avec l'authentification)
        const userId = 1; // Temporaire: à remplacer par l'ID réel de l'utilisateur
        
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
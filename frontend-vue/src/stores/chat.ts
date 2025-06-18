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
        console.log('Chargement des messages pour la room:', roomId);
        const response = await axios.get(`${API_URL}/api/chat/room/${roomId}`);
        console.log('Messages reçus:', response.data);
        
        this.messages = response.data.map((msg: any) => ({
          ...msg,
          color: this.getUserColor(msg.username)
        }));
      } catch (error) {
        console.error('Erreur lors du chargement des messages:', error);
      } finally {
        this.isLoading = false;
      }
    },
    
    // Envoyer un message
    async sendMessage(data: { room_id: number, message: string }) {
      try {
        console.log('Envoi de message via le store:', data);
        
        // Récupérer l'ID utilisateur depuis le store d'authentification
        const authStore = useAuthStore();
        const userId = authStore.user?.id;
        
        if (!userId) {
          console.warn("Tentative d'envoi de message sans être connecté");
          throw new Error("Vous devez être connecté pour envoyer des messages");
        }
        
        // Préparer les données de la requête
        const requestData = {
          room_id: data.room_id,
          message: data.message,
          user_id: userId
        };
        
        console.log('Requête POST vers /api/chat/ avec données:', requestData);
        
        const response = await axios.post(`${API_URL}/api/chat/`, requestData);
        console.log('Réponse du serveur:', response.data);
        
        // Le message sera ajouté via WebSocket dans le store de la salle
        return response.data;
      } catch (error) {
        console.error('Erreur détaillée lors de l\'envoi du message:', error);
        throw error;
      }
    },
    
    // Ajouter un message (reçu via WebSocket ou local)
    addMessage(message: any) {
      console.log('Ajout de message dans le store chat:', message);
      
      // Empêcher les doublons en vérifiant l'ID du message
      if (message.id && typeof message.id === 'number' && 
          this.messages.some(m => m.id === message.id)) {
        console.log('Message déjà présent, ignoré');
        return;
      }
      
      // Adapter le format si nécessaire
      const formattedMessage = {
        ...message,
        // S'assurer que nous avons une couleur
        color: message.color || this.getUserColor(message.username || 'Anonyme')
      };
      
      console.log('Message formaté:', formattedMessage);
      this.messages.push(formattedMessage);
      
      // Limiter le nombre de messages (garder les 100 derniers)
      if (this.messages.length > 100) {
        this.messages = this.messages.slice(-100);
      }
    },
    
    // Générer une couleur pour un utilisateur
    getUserColor(username: string): string {
      // Pour les messages système
      if (username === 'Système') {
        return '#1db954';
      }
      
      // Générer une couleur basée sur le nom d'utilisateur
      let hash = 0;
      for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash);
      }
      
      // Générer une couleur pastel claire
      const h = Math.abs(hash) % 360;
      const s = 70 + Math.abs(hash) % 30; // 70-100%
      const l = 60 + Math.abs(hash) % 20; // 60-80%
      
      return `hsl(${h}, ${s}%, ${l}%)`;
    },
    
    // Effacer les messages
    clearMessages() {
      this.messages = [];
    }
  }
}); 
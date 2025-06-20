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
        const roomStore = useRoomStore();
        const userId = authStore.user?.id;
        
        if (!userId) {
          console.warn("Tentative d'envoi de message sans être connecté");
          throw new Error("Vous devez être connecté pour envoyer des messages");
        }
        
        // Vérifier l'état de la connexion
        if (!roomStore.isConnected) {
          console.warn("Tentative d'envoi de message avec WebSocket déconnecté");
          throw new Error("La connexion au serveur a été perdue");
        }
        
        // Préparer les données de la requête
        const requestData = {
          room_id: data.room_id,
          message: data.message,
          user_id: userId
        };
        
        console.log('Requête POST vers /api/chat/ avec données:', requestData);
        
        // Ajouter un timeout pour éviter de bloquer l'interface indéfiniment
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        try {
          const response = await axios.post(`${API_URL}/api/chat/`, requestData, {
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          console.log('Réponse du serveur:', response.data);
          
          // Mettre à jour les messages locaux pour remplacer le message temporaire
          // par la version confirmée par le serveur
          const confirmedMessageId = response.data.id;
          const tempMessageIndex = this.messages.findIndex(
            m => m.message === data.message && 
            typeof m.id === 'string' && 
            m.id.startsWith('local-')
          );
          
          if (tempMessageIndex !== -1) {
            // Si on trouve le message temporaire, on le remplace
            this.messages[tempMessageIndex] = {
              ...this.messages[tempMessageIndex],
              id: confirmedMessageId
            };
            console.log('Message temporaire remplacé par message confirmé:', confirmedMessageId);
          }
          
          return response.data;
        } catch (axiosError: any) {
          clearTimeout(timeoutId);
          console.error('Erreur Axios:', axiosError);
          
          if (axiosError.name === 'AbortError' || axiosError.code === 'ECONNABORTED') {
            throw new Error('Le serveur met trop de temps à répondre. Veuillez réessayer.');
          }
          
          if (axiosError.response) {
            console.error('Données de la réponse d\'erreur:', axiosError.response.data);
            console.error('Statut de la réponse d\'erreur:', axiosError.response.status);
            console.error('Headers de la réponse d\'erreur:', axiosError.response.headers);
            
            // Erreur spécifique selon le code HTTP
            if (axiosError.response.status === 404) {
              throw new Error('Salle non trouvée.');
            } else if (axiosError.response.status === 401 || axiosError.response.status === 403) {
              throw new Error('Non autorisé à envoyer des messages.');
            } else {
              const errorMsg = axiosError.response.data.detail || 'Erreur lors de l\'envoi du message.';
              throw new Error(errorMsg);
            }
          } else if (axiosError.request) {
            console.error('Requête envoyée mais pas de réponse:', axiosError.request);
            throw new Error('Pas de réponse du serveur. Vérifiez votre connexion.');
          } else {
            console.error('Erreur de configuration de la requête:', axiosError.message);
            throw new Error(axiosError.message);
          }
        }
      } catch (error) {
        console.error('Erreur détaillée lors de l\'envoi du message:', error);
        throw error;
      }
    },
    
    // Ajouter un message (reçu via WebSocket ou local)
    addMessage(message: any) {
      console.log('Ajout de message dans le store chat:', message);
      
      // Empêcher les doublons de messages serveur (avec ID numérique)
      if (message.id && typeof message.id === 'number') {
        const exists = this.messages.some(m => m.id === message.id);
        if (exists) {
          console.log('Message avec ID serveur déjà présent, ignoré:', message.id);
          return;
        }
      }
      
      // Adapter le format si nécessaire
      const formattedMessage = {
        ...message,
        // S'assurer que nous avons une couleur
        color: message.color || this.getUserColor(message.username || 'Anonyme'),
        // S'assurer que le champ sent_at est toujours présent
        sent_at: message.sent_at || new Date().toISOString()
      };
      
      console.log('Message formaté pour ajout:', formattedMessage);
      
      // Recréer le tableau pour déclencher la réactivité
      this.messages = [...this.messages, formattedMessage];
      
      // Limiter le nombre de messages (garder les 100 derniers)
      if (this.messages.length > 100) {
        this.messages = this.messages.slice(-100);
      }
      
      console.log('Nombre de messages après ajout:', this.messages.length);
      
      // Émettre un événement pour notifier les composants intéressés
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('new-chat-message', { 
          detail: formattedMessage 
        }));
      }, 0);
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
import { defineStore } from 'pinia';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useRoomStore = defineStore('room', {
  state: () => ({
    currentRoom: null as any,
    isConnected: false,
    socket: null as WebSocket | null,
    users: [] as any[],
    playbackUpdateCallbacks: [] as Function[]
  }),
  
  actions: {
    // Rejoindre une salle
    async joinRoom(roomCode: string) {
      try {
        // Vérifier si la salle existe
        const response = await axios.get(`${API_URL}/api/rooms/${roomCode}`);
        this.currentRoom = response.data;
        
        // Établir une connexion WebSocket
        this.connectWebSocket(roomCode);
        
        return this.currentRoom;
      } catch (error) {
        // Si la salle n'existe pas, la créer
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          return this.createRoom(roomCode);
        }
        throw error;
      }
    },
    
    // Créer une nouvelle salle
    async createRoom(roomCode: string) {
      const response = await axios.post(`${API_URL}/api/rooms/`, {
        name: `Salle ${roomCode}`,
        room_code: roomCode
      });
      
      this.currentRoom = response.data;
      
      // Établir une connexion WebSocket
      this.connectWebSocket(roomCode);
      
      return this.currentRoom;
    },
    
    // Établir une connexion WebSocket
    connectWebSocket(roomCode: string) {
      // Fermer la connexion existante si elle existe
      if (this.socket) {
        this.socket.close();
      }
      
      // Récupérer l'ID utilisateur (à implémenter avec l'authentification)
      const userId = 1; // Temporaire: à remplacer par l'ID réel de l'utilisateur
      
      // Créer une nouvelle connexion
      this.socket = new WebSocket(`${API_URL.replace('http', 'ws')}/api/rooms/ws/${roomCode}/${userId}`);
      
      // Gestionnaire d'événements
      this.socket.onopen = () => {
        this.isConnected = true;
        console.log('WebSocket connecté');
      };
      
      this.socket.onclose = () => {
        this.isConnected = false;
        console.log('WebSocket déconnecté');
      };
      
      this.socket.onerror = (error) => {
        console.error('Erreur WebSocket:', error);
      };
      
      this.socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Traiter les différents types de messages
        switch (data.type) {
          case 'user_joined':
          case 'user_left':
            // Mettre à jour la liste des utilisateurs
            this.updateUsersList(data);
            break;
          
          case 'play':
          case 'pause':
          case 'seek':
            // Notifier les callbacks de mise à jour de lecture
            this.notifyPlaybackUpdate(data);
            break;
        }
      };
    },
    
    // Quitter la salle
    leaveRoom() {
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
      
      this.currentRoom = null;
      this.isConnected = false;
      this.users = [];
    },
    
    // Mettre à jour la liste des utilisateurs
    updateUsersList(data: any) {
      // À implémenter: mettre à jour la liste des utilisateurs connectés
      console.log('Utilisateurs connectés:', data.users_count);
    },
    
    // Envoyer une mise à jour de lecture
    sendPlaybackUpdate(update: any) {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket non connecté');
        return;
      }
      
      this.socket.send(JSON.stringify({
        type: 'playback_update',
        ...update
      }));
    },
    
    // S'abonner aux mises à jour de lecture
    onPlaybackUpdate(callback: Function) {
      this.playbackUpdateCallbacks.push(callback);
    },
    
    // Notifier les callbacks de mise à jour de lecture
    notifyPlaybackUpdate(data: any) {
      this.playbackUpdateCallbacks.forEach(callback => callback(data));
    }
  }
}); 
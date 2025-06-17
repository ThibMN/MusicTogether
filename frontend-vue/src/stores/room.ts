import { defineStore } from 'pinia';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 2000; // 2 secondes
const PING_INTERVAL = 30000; // 30 secondes

export const useRoomStore = defineStore('room', {
  state: () => ({
    currentRoom: null as any,
    isConnected: false,
    socket: null as WebSocket | null,
    users: [] as any[],
    playbackUpdateCallbacks: [] as Function[],
    reconnectAttempts: 0,
    reconnectTimer: null as ReturnType<typeof setTimeout> | null,
    isReconnecting: false,
    lastRoomCode: '' as string,
    pingTimer: null as ReturnType<typeof setInterval> | null,
    lastPongTime: 0,
    clientId: '' as string
  }),
  
  actions: {
    // Rejoindre une salle
    async joinRoom(roomCode: string) {
      try {
        console.log(`Tentative de connexion à la salle: ${roomCode}`);
        // Vérifier si la salle existe
        const response = await axios.get(`${API_URL}/api/rooms/${roomCode}`);
        console.log('Réponse du serveur:', response.data);
        this.currentRoom = response.data;
        this.lastRoomCode = roomCode;
        
        // Établir une connexion WebSocket
        await this.connectWebSocket(roomCode);
        
        return this.currentRoom;
      } catch (error) {
        console.error('Erreur détaillée lors de la connexion à la salle:', error);
        
        // Si la salle n'existe pas, la créer
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          console.log('Salle non trouvée, tentative de création...');
          return this.createRoom(roomCode);
        }
        throw error;
      }
    },
    
    // Créer une nouvelle salle
    async createRoom(roomCode: string) {
      try {
        console.log('Tentative de création de la salle:', roomCode);
        
        const response = await axios.post(`${API_URL}/api/rooms/`, {
          name: `Salle ${roomCode}`,
          room_code: roomCode
        });
        
        console.log('Salle créée avec succès:', response.data);
        this.currentRoom = response.data;
        this.lastRoomCode = roomCode;
        
        // Établir une connexion WebSocket
        await this.connectWebSocket(roomCode);
        
        return this.currentRoom;
      } catch (error) {
        console.error('Erreur lors de la création de la salle:', error);
        throw error;
      }
    },
    
    // Établir une connexion WebSocket
    async connectWebSocket(roomCode: string) {
      return new Promise<void>((resolve, reject) => {
        // Fermer la connexion existante si elle existe
        if (this.socket) {
          this.socket.close();
        }
        
        // Arrêter le ping existant s'il y en a un
        this.stopPing();
        
        // Récupérer l'ID utilisateur (à implémenter avec l'authentification)
        const userId = 1; // Temporaire: à remplacer par l'ID réel de l'utilisateur
        
        // Créer une nouvelle connexion
        const wsUrl = `${API_URL.replace('http', 'ws')}/api/rooms/ws/${roomCode}/${userId}`;
        console.log('Tentative de connexion WebSocket à:', wsUrl);
        
        try {
          this.socket = new WebSocket(wsUrl);
          
          // Gestionnaire d'événements
          this.socket.onopen = () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.isReconnecting = false;
            console.log('WebSocket connecté avec succès');
            
            // Démarrer le ping
            this.startPing();
            
            resolve();
          };
          
          this.socket.onclose = (event) => {
            this.isConnected = false;
            console.log(`WebSocket déconnecté avec code: ${event.code}, raison: ${event.reason}`);
            
            // Arrêter le ping
            this.stopPing();
            
            // Tenter une reconnexion si la déconnexion n'est pas volontaire
            if (this.currentRoom && !event.wasClean && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              this.attemptReconnect(roomCode);
            }
            
            // Si la connexion n'a pas encore été établie, rejeter la promesse
            if (!this.isConnected) {
              reject(new Error(`WebSocket déconnecté avec code: ${event.code}`));
            }
          };
          
          this.socket.onerror = (error) => {
            console.error('Erreur WebSocket détaillée:', error);
            
            // Rejeter la promesse si l'erreur se produit pendant la connexion
            if (!this.isConnected) {
              reject(error);
            }
          };
          
          this.socket.onmessage = (event) => {
            console.log('Message WebSocket reçu:', event.data);
            try {
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
                  
                case 'pong':
                  // Mettre à jour le timestamp du dernier pong reçu
                  this.lastPongTime = Date.now();
                  break;
              }
            } catch (error) {
              console.error('Erreur lors du traitement du message WebSocket:', error);
            }
          };
          
          // Ajouter un timeout pour la connexion
          setTimeout(() => {
            if (!this.isConnected && this.socket && this.socket.readyState !== WebSocket.OPEN) {
              console.error('Timeout de connexion WebSocket');
              this.socket.close();
              reject(new Error('Timeout de connexion WebSocket'));
            }
          }, 10000); // 10 secondes de timeout
        } catch (error) {
          console.error('Erreur lors de la création du WebSocket:', error);
          reject(error);
        }
      });
    },
    
    // Démarrer le ping périodique pour maintenir la connexion active
    startPing() {
      this.lastPongTime = Date.now();
      
      // Nettoyer l'ancien timer s'il existe
      this.stopPing();
      
      // Créer un nouveau timer de ping
      this.pingTimer = setInterval(() => {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          console.log('Envoi d\'un ping WebSocket...');
          try {
            this.socket.send(JSON.stringify({ type: 'ping' }));
            
            // Vérifier si nous avons reçu un pong récemment
            const timeSinceLastPong = Date.now() - this.lastPongTime;
            if (timeSinceLastPong > PING_INTERVAL * 2) {
              console.warn(`Pas de pong reçu depuis ${timeSinceLastPong}ms, la connexion est peut-être morte`);
              
              // Fermer la connexion pour forcer une reconnexion
              if (this.socket) {
                this.socket.close();
                this.socket = null;
              }
              
              // Tenter une reconnexion si nous avons un code de salle
              if (this.lastRoomCode && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                this.attemptReconnect(this.lastRoomCode);
              }
            }
          } catch (e) {
            console.error('Erreur lors de l\'envoi du ping:', e);
          }
        }
      }, PING_INTERVAL);
    },
    
    // Arrêter le ping périodique
    stopPing() {
      if (this.pingTimer) {
        clearInterval(this.pingTimer);
        this.pingTimer = null;
      }
    },
    
    // Tenter une reconnexion WebSocket
    attemptReconnect(roomCode: string) {
      if (this.isReconnecting || this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
      
      this.isReconnecting = true;
      this.reconnectAttempts++;
      
      console.log(`Tentative de reconnexion ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} dans ${RECONNECT_DELAY}ms`);
      
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
      }
      
      this.reconnectTimer = setTimeout(() => {
        console.log(`Reconnexion à la salle ${roomCode}...`);
        try {
          this.connectWebSocket(roomCode)
            .then(() => {
              this.isReconnecting = false;
              console.log('Reconnexion réussie');
            })
            .catch(error => {
              console.error('Erreur lors de la tentative de reconnexion:', error);
              this.isReconnecting = false;
              
              // Si nous avons atteint le nombre maximum de tentatives, arrêter les reconnexions
              if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
                console.error('Nombre maximum de tentatives de reconnexion atteint');
              }
            });
        } catch (error) {
          console.error('Erreur lors de la tentative de reconnexion:', error);
          this.isReconnecting = false;
        }
      }, RECONNECT_DELAY * this.reconnectAttempts); // Augmenter le délai à chaque tentative
    },
    
    // Quitter la salle
    leaveRoom() {
      // Annuler toute tentative de reconnexion en cours
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      
      // Arrêter le ping
      this.stopPing();
      
      this.isReconnecting = false;
      this.reconnectAttempts = 0;
      
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
      
      this.currentRoom = null;
      this.isConnected = false;
      this.users = [];
      this.lastRoomCode = '';
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
      
      // Limiter les mises à jour trop fréquentes du même type
      const now = Date.now();
      const lastUpdateType = `last_${update.type}_update`;
      const lastUpdateTime = this[lastUpdateType as keyof typeof this] as number | undefined;
      
      // Minimum 200ms entre les mises à jour du même type, sauf pour sync qui doit suivre son interval
      if (lastUpdateTime && now - lastUpdateTime < 200 && update.type !== 'sync') {
        console.log(`Mise à jour de type ${update.type} ignorée (trop fréquente)`);
        return;
      }
      
      // Mettre à jour le timestamp de dernière mise à jour
      this[lastUpdateType as keyof typeof this] = now;
      
      // Ajouter un ID unique de client pour identifier la source de la mise à jour
      update.client_id = this.clientId;
      
      console.log(`Envoi mise à jour WebSocket: ${JSON.stringify(update)}`);
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
      try {
        // Ignorer les mises à jour provenant de nous-mêmes
        if (data.client_id === this.clientId) {
          console.log(`Mise à jour ignorée (provient du même client): ${JSON.stringify(data)}`);
          return;
        }
        
        console.log(`Traitement mise à jour WebSocket: ${JSON.stringify(data)}`);
        this.playbackUpdateCallbacks.forEach(callback => callback(data));
      } catch (error) {
        console.error('Erreur lors du traitement de la mise à jour:', error);
      }
    }
  }
});
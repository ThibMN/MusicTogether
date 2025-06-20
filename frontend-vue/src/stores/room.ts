import { defineStore } from 'pinia';
import axios from 'axios';
import { useAuthStore } from './auth';
import { useQueueStore } from './queue';
import { useChatStore } from './chat';

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
    chatMessageCallbacks: [] as Function[],
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
        
        // Récupérer l'ID de l'utilisateur connecté
        const authStore = useAuthStore();
        const userId = authStore.user?.id;
        
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
        
        // Récupérer l'ID de l'utilisateur connecté
        const authStore = useAuthStore();
        const userId = authStore.user?.id;
        
        const response = await axios.post(`${API_URL}/api/rooms/`, {
          name: `Salle ${roomCode}`,
          room_code: roomCode,
          creator_id: userId || null // Envoyer l'id du créateur
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
        
        // Récupérer l'ID utilisateur depuis le store d'authentification
        const authStore = useAuthStore();
        const userId = authStore.user?.id || 0; // Utiliser 0 pour les utilisateurs non connectés
        
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
              
              // Priorité maximale pour les messages de chat
              if (data.type === 'chat_message') {
                console.log('Message de chat reçu en priorité:', data.message);
                
                // Notifier avec les callbacks spécifiques de chat
                this.notifyChatMessage(data);
                
                // Si un message est reçu via WebSocket, on est certain que la connexion fonctionne
                this.isConnected = true;
                
                // Et vérifier si un message temporaire existe pour le remplacer
                if (data.message && data.message.id) {
                  const chatStore = useChatStore();
                  const localMsgIndex = chatStore.messages.findIndex(
                    m => typeof m.id === 'string' && 
                    m.id.startsWith('local-') && 
                    m.message === data.message.message &&
                    m.username === data.message.username
                  );
                  
                  if (localMsgIndex !== -1) {
                    console.log('Message temporaire trouvé, remplacement par version serveur');
                    
                    // Remplacer le message temporaire par la version du serveur
                    // en créant une nouvelle référence pour forcer la réactivité
                    const updatedMessages = [...chatStore.messages];
                    updatedMessages[localMsgIndex] = {
                      ...updatedMessages[localMsgIndex],
                      id: data.message.id
                    };
                    chatStore.messages = updatedMessages;
                  }
                }
                return; // Sortir après avoir traité le message de chat
              }
              
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
                case 'track_change':
                  // Notifier les callbacks de mise à jour de lecture
                  this.notifyPlaybackUpdate(data);
                  break;
                
                case 'queue_change':
                  // Gérer les changements dans la file d'attente
                  this.handleQueueChange(data);
                  break;
                
                case 'queue_sync':
                  // Synchroniser la file d'attente
                  this.synchronizeQueue(data);
                  break;
                  
                case 'pong':
                  // Mettre à jour le timestamp du dernier pong reçu
                  this.lastPongTime = Date.now();
                  break;
                
                case 'playback_state_response':
                  // Synchroniser l'état de lecture initial
                  this.notifyPlaybackUpdate(data);
                  break;
                
                default:
                  console.log('Type de message WebSocket non géré:', data.type);
                  // Transmettre quand même aux callbacks car ils pourraient le traiter
                  this.notifyPlaybackUpdate(data);
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
      if (this.isReconnecting) return;
      
      this.isReconnecting = true;
      this.reconnectAttempts++;
      
      console.log(`Tentative de reconnexion ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} dans ${RECONNECT_DELAY}ms`);
      
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
      }
      
      // Calculer un délai exponentiel pour éviter de surcharger le serveur
      // Plus d'échecs = attente plus longue
      const exponentialDelay = RECONNECT_DELAY * Math.pow(1.5, this.reconnectAttempts - 1);
      const actualDelay = Math.min(exponentialDelay, 10000); // Max 10 secondes
      
      this.reconnectTimer = setTimeout(async () => {
        try {
          console.log('Tentative de reconnexion WebSocket...');
          
          // Fermer la connexion existante si elle existe
          if (this.socket) {
            this.socket.close();
            this.socket = null;
          }
          
          await this.connectWebSocket(roomCode);
          console.log('Reconnexion WebSocket réussie');
          this.isReconnecting = false;
          this.isConnected = true;
          
          // Demander une mise à jour de l'état de lecture, de la file d'attente et des messages
          this.requestStateUpdate();
          
          // Recharger aussi les messages de chat après reconnexion
          const chatStore = useChatStore();
          if (this.currentRoom) {
            chatStore.loadMessages(this.currentRoom.id);
          }
          
          console.log('État après reconnexion: connecté =', this.isConnected);
        } catch (error) {
          console.error('Erreur lors de la reconnexion WebSocket:', error);
          this.isReconnecting = false;
          this.isConnected = false;
          
          // Tenter une nouvelle reconnexion si on n'a pas atteint le nombre maximum de tentatives
          if (this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            this.attemptReconnect(roomCode);
          } else {
            console.error('Nombre maximum de tentatives de reconnexion atteint');
            // Émettre un événement global pour notifier l'utilisateur
            window.dispatchEvent(new CustomEvent('websocket-connection-failed'));
          }
        }
      }, actualDelay);
    },
    
    // Quitter la salle actuelle
    leaveRoom() {
      console.log('Quitter la salle...');
      
      // Fermer la connexion WebSocket
      if (this.socket) {
        this.socket.close(1000, 'Déconnexion volontaire'); // 1000 = code de fermeture normale
        this.socket = null;
      }
      
      // Arrêter le ping
      this.stopPing();
      
      // Arrêter toute tentative de reconnexion en cours
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      
      // Réinitialiser l'état
      this.isConnected = false;
      this.currentRoom = null;
      this.reconnectAttempts = 0;
      this.isReconnecting = false;
      this.lastRoomCode = '';
    },
    
    // Mettre à jour la liste des utilisateurs connectés
    updateUsersList(data: any) {
      console.log('Mise à jour de la liste des utilisateurs:', data);
      
      // Ici, on peut mettre à jour une liste d'utilisateurs connectés
      // pour afficher dans l'interface qui est en ligne
    },
    
    // Envoyer une mise à jour de lecture à tous les utilisateurs
    sendPlaybackUpdate(update: any) {
      if (!this.isConnected || !this.socket) {
        console.warn('Impossible d\'envoyer une mise à jour: non connecté');
        return;
      }
      
      // Ajouter l'ID client pour identifier la source
      const updateWithClientId = {
        ...update,
        client_id: this.clientId
      };
      
      try {
        this.socket.send(JSON.stringify(updateWithClientId));
      } catch (error) {
        console.error('Erreur lors de l\'envoi de la mise à jour:', error);
      }
    },
    
    // S'abonner aux mises à jour de lecture
    onPlaybackUpdate(callback: Function) {
      this.playbackUpdateCallbacks.push(callback);
    },
    
    // Notifier les callbacks de mise à jour de lecture
    notifyPlaybackUpdate(data: any) {
      this.playbackUpdateCallbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Erreur dans un callback de mise à jour de lecture:', error);
        }
      });
    },
    
    // Gérer les changements dans la file d'attente
    handleQueueChange(data: any) {
      console.log('Changement dans la file d\'attente reçu:', data);
      
      // Synchroniser la file d'attente si disponible
      if (data.queue) {
        const queueStore = useQueueStore();
        queueStore.syncQueueWithRemote(data.queue);
      } else if (data.currentTrackId) {
        // Sinon, synchroniser juste la piste actuelle
        const queueStore = useQueueStore();
        queueStore.syncCurrentTrack(data.currentTrackId);
      }
      
      // Notifier les callbacks
      this.notifyPlaybackUpdate(data);
    },
    
    // Synchroniser la file d'attente
    synchronizeQueue(data: any) {
      if (data.queue) {
        const queueStore = useQueueStore();
        queueStore.syncQueueWithRemote(data.queue);
      }
    },
    
    // Demander une mise à jour de l'état après reconnexion
    requestStateUpdate() {
      if (!this.isConnected || !this.socket) {
        console.warn('Impossible de demander une mise à jour: non connecté');
        return;
      }
      
      // Demander l'état de lecture
      this.socket.send(JSON.stringify({
        type: 'request_playback_state',
        for_user_id: this.clientId
      }));
      
      // Demander la file d'attente
      this.socket.send(JSON.stringify({
        type: 'request_queue'
      }));
    },
    
    // S'abonner aux mises à jour de chat
    onChatMessage(callback: Function) {
      this.chatMessageCallbacks.push(callback);
    },
    
    // Notifier les callbacks de message chat
    notifyChatMessage(data: any) {
      console.log('Notification spécifique de message chat aux callbacks:', this.chatMessageCallbacks.length);
      this.chatMessageCallbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Erreur dans un callback de message chat:', error);
        }
      });
      
      // Notifier aussi les callbacks généraux
      this.notifyPlaybackUpdate(data);
    }
  }
});
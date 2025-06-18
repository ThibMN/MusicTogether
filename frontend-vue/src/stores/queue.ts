import { defineStore } from 'pinia';
import axios from 'axios';
import { useMusicStore } from './music';
import { useRoomStore } from './room';
import { useAuthStore } from './auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useQueueStore = defineStore('queue', {
  state: () => ({
    queueItems: [] as any[],
    isLoading: false,
    currentIndex: -1
  }),
  
  actions: {
    // Charger la file d'attente d'une salle
    async loadQueue(roomId: number | undefined) {
      if (!roomId) return;
      
      this.isLoading = true;
      try {
        const response = await axios.get(`${API_URL}/api/queue/rooms/${roomId}`);
        this.queueItems = response.data;
        
        // Si la file n'est pas vide et qu'aucune piste n'est sélectionnée, sélectionner la première
        if (this.queueItems.length > 0 && this.currentIndex === -1) {
          this.currentIndex = 0;
          await this.updateCurrentTrack();
        }
        
        // Notifier les autres utilisateurs de la file d'attente actuelle
        this.broadcastQueueUpdate();
      } catch (error) {
        console.error('Erreur lors du chargement de la file d\'attente:', error);
      } finally {
        this.isLoading = false;
      }
    },
    
    // Ajouter une musique à la file d'attente
    async addToQueue(data: { room_id: number, music_id: number }) {
      try {
        // Récupérer l'ID utilisateur depuis le store d'authentification
        const authStore = useAuthStore();
        const userId = authStore.user?.id;
        
        // Ajouter l'ID utilisateur à la requête
        const requestData = {
          ...data,
          user_id: userId || null
        };
        
        const response = await axios.post(`${API_URL}/api/queue/items`, requestData);
        
        // Ajouter l'élément à la file d'attente locale
        const musicStore = useMusicStore();
        const musicDetails = await musicStore.getMusicDetails(data.music_id);
        
        this.queueItems.push({
          ...response.data,
          music: musicDetails,
          user_id: userId // S'assurer que l'ID utilisateur est bien présent dans l'objet local
        });
        
        // Si c'est le premier élément, le sélectionner
        if (this.queueItems.length === 1) {
          this.currentIndex = 0;
          await this.updateCurrentTrack();
        }
        
        // Notifier les autres utilisateurs du changement de file d'attente
        this.broadcastQueueUpdate();
        
        return response.data;
      } catch (error) {
        console.error('Erreur lors de l\'ajout à la file d\'attente:', error);
        throw error;
      }
    },
    
    // Supprimer une musique de la file d'attente
    async removeFromQueue(queueItemId: number) {
      try {
        // Vérifier si l'utilisateur a le droit de supprimer cet élément
        const authStore = useAuthStore();
        const userId = authStore.user?.id;
        
        // Trouver l'élément dans la file d'attente
        const item = this.queueItems.find(item => item.id === queueItemId);
        
        // Vérifier si l'utilisateur est autorisé à supprimer cet élément
        // (propriétaire de l'élément ou aucun propriétaire spécifié)
        if (item && userId && item.user_id && item.user_id !== userId) {
          console.warn("Tentative de suppression d'un élément ajouté par un autre utilisateur");
          // On pourrait lancer une erreur ici, mais on va laisser le backend gérer les permissions
        }
        
        await axios.delete(`${API_URL}/api/queue/${queueItemId}`);
        
        // Trouver l'index de l'élément à supprimer
        const index = this.queueItems.findIndex(item => item.id === queueItemId);
        
        // Si l'élément existe, le supprimer
        if (index !== -1) {
          // Si l'élément à supprimer est l'élément actuel
          if (index === this.currentIndex) {
            // Passer à l'élément suivant s'il existe
            if (index < this.queueItems.length - 1) {
              // Ne pas changer currentIndex car l'élément suivant prendra sa place
            } else if (this.queueItems.length > 1) {
              // Sinon, revenir à l'élément précédent
              this.currentIndex = index - 1;
            } else {
              // S'il n'y a plus d'éléments
              this.currentIndex = -1;
            }
          } else if (index < this.currentIndex) {
            // Si l'élément à supprimer est avant l'élément actuel, ajuster l'index
            this.currentIndex--;
          }
          
          // Supprimer l'élément
          this.queueItems.splice(index, 1);
          
          // Mettre à jour la piste actuelle
          await this.updateCurrentTrack();
          
          // Notifier les autres utilisateurs du changement de file d'attente
          this.broadcastQueueUpdate();
        }
      } catch (error) {
        console.error('Erreur lors de la suppression de la file d\'attente:', error);
        throw error;
      }
    },
    
    // Réorganiser la file d'attente
    async reorderQueue(sourceItemId: number, targetItemId: number) {
      // Trouver les éléments source et cible
      const sourceIndex = this.queueItems.findIndex(item => item.id === sourceItemId);
      const targetIndex = this.queueItems.findIndex(item => item.id === targetItemId);
      
      if (sourceIndex === -1 || targetIndex === -1) return;
      
      try {
        // Calculer la nouvelle position
        const sourceItem = this.queueItems[sourceIndex];
        const targetItem = this.queueItems[targetIndex];
        
        // Mettre à jour sur le serveur
        await axios.put(`${API_URL}/api/queue/${sourceItemId}`, {
          position: targetItem.position
        });
        
        // Mettre à jour localement
        const item = this.queueItems.splice(sourceIndex, 1)[0];
        this.queueItems.splice(targetIndex, 0, item);
        
        // Mettre à jour l'index actuel si nécessaire
        if (this.currentIndex === sourceIndex) {
          this.currentIndex = targetIndex;
        } else if (sourceIndex < this.currentIndex && targetIndex >= this.currentIndex) {
          this.currentIndex--;
        } else if (sourceIndex > this.currentIndex && targetIndex <= this.currentIndex) {
          this.currentIndex++;
        }
        
        // Notifier les autres utilisateurs du changement de file d'attente
        this.broadcastQueueUpdate();
      } catch (error) {
        console.error('Erreur lors de la réorganisation de la file d\'attente:', error);
        // Recharger la file d'attente en cas d'erreur
        const roomId = this.queueItems[0]?.room_id;
        if (roomId) {
          await this.loadQueue(roomId);
        }
      }
    },
    
    // Jouer une piste spécifique
    async playTrack(musicId: number) {
      const index = this.queueItems.findIndex(item => item.music.id === musicId);
      if (index !== -1) {
        this.currentIndex = index;
        await this.updateCurrentTrack();
        
        // Notifier les autres utilisateurs du changement de piste
        const roomStore = useRoomStore();
        if (roomStore.isConnected) {
          roomStore.sendPlaybackUpdate({
            type: 'track_change',
            trackId: musicId,
            position: 0,
            isPlaying: true
          });
        }
        
        return true;
      }
      return false;
    },
    
    // Passer à la piste suivante
    async playNextTrack() {
      if (this.currentIndex < this.queueItems.length - 1) {
        this.currentIndex++;
        await this.updateCurrentTrack();
        return true;
      }
      return false;
    },
    
    // Revenir à la piste précédente
    async playPreviousTrack() {
      if (this.currentIndex > 0) {
        this.currentIndex--;
        await this.updateCurrentTrack();
        return true;
      }
      return false;
    },
    
    // Mettre à jour la piste actuelle
    async updateCurrentTrack() {
      const musicStore = useMusicStore();
      
      if (this.currentIndex >= 0 && this.currentIndex < this.queueItems.length) {
        const currentItem = this.queueItems[this.currentIndex];
        musicStore.setCurrentTrack(currentItem.music);
      } else {
        musicStore.setCurrentTrack(null);
      }
    },
    
    // Notifier les autres utilisateurs d'un changement dans la file d'attente (notification simple)
    notifyQueueChange() {
      const roomStore = useRoomStore();
      if (roomStore.isConnected && this.queueItems.length > 0) {
        const currentMusicId = this.currentIndex >= 0 && this.currentIndex < this.queueItems.length
          ? this.queueItems[this.currentIndex].music.id
          : null;
          
        roomStore.sendPlaybackUpdate({
          type: 'queue_change',
          currentTrackId: currentMusicId,
          queueLength: this.queueItems.length
        });
      }
    },
    
    // Diffuser la file d'attente complète à tous les utilisateurs de la salle
    broadcastQueueUpdate() {
      const roomStore = useRoomStore();
      if (roomStore.isConnected) {
        const currentMusicId = this.currentIndex >= 0 && this.currentIndex < this.queueItems.length
          ? this.queueItems[this.currentIndex].music.id
          : null;
          
        roomStore.sendPlaybackUpdate({
          type: 'queue_change',
          currentTrackId: currentMusicId,
          queueLength: this.queueItems.length,
          queue: this.queueItems // Envoyer la file d'attente complète
        });
      }
    },
    
    // Synchroniser avec la file d'attente reçue
    syncQueueWithRemote(queue: any[]) {
      if (!queue || !Array.isArray(queue) || queue.length === 0) return false;
      
      console.log('Synchronisation de la file d\'attente:', queue);
      
      // Sauvegarder le morceau actuel s'il existe
      const currentTrackId = this.currentIndex >= 0 && this.currentIndex < this.queueItems.length
        ? this.queueItems[this.currentIndex].music.id
        : null;
      
      // Mettre à jour la file d'attente locale
      this.queueItems = queue;
      
      // Si nous avions un morceau actuel, essayer de trouver son nouvel index
      if (currentTrackId) {
        const newIndex = this.queueItems.findIndex(item => item.music.id === currentTrackId);
        if (newIndex !== -1) {
          this.currentIndex = newIndex;
        } else {
          // Si le morceau n'est plus dans la file d'attente, prendre le premier
          this.currentIndex = this.queueItems.length > 0 ? 0 : -1;
        }
      } else {
        // Si aucun morceau n'était actif, prendre le premier
        this.currentIndex = this.queueItems.length > 0 ? 0 : -1;
      }
      
      // Mettre à jour le morceau actuel
      this.updateCurrentTrack();
      
      return true;
    },
    
    // Synchroniser l'index courant de la file d'attente
    syncCurrentTrack(trackId: number) {
      if (!trackId) return false;
      
      // Chercher la piste dans la file d'attente
      const index = this.queueItems.findIndex(item => item.music.id === trackId);
      
      // Si la piste existe dans la file d'attente et n'est pas déjà l'élément courant
      if (index !== -1 && this.currentIndex !== index) {
        this.currentIndex = index;
        this.updateCurrentTrack();
        return true;
      }
      
      return false;
    }
  }
}); 
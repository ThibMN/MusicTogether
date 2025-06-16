import { defineStore } from 'pinia';
import axios from 'axios';
import { useMusicStore } from './music';

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
        const response = await axios.get(`${API_URL}/api/queue/room/${roomId}`);
        this.queueItems = response.data;
        
        // Si la file n'est pas vide et qu'aucune piste n'est sélectionnée, sélectionner la première
        if (this.queueItems.length > 0 && this.currentIndex === -1) {
          this.currentIndex = 0;
          await this.updateCurrentTrack();
        }
      } catch (error) {
        console.error('Erreur lors du chargement de la file d\'attente:', error);
      } finally {
        this.isLoading = false;
      }
    },
    
    // Ajouter une musique à la file d'attente
    async addToQueue(data: { room_id: number, music_id: number }) {
      try {
        const response = await axios.post(`${API_URL}/api/queue/`, data);
        
        // Ajouter l'élément à la file d'attente locale
        const musicStore = useMusicStore();
        const musicDetails = await musicStore.getMusicDetails(data.music_id);
        
        this.queueItems.push({
          ...response.data,
          music: musicDetails
        });
        
        // Si c'est le premier élément, le sélectionner
        if (this.queueItems.length === 1) {
          this.currentIndex = 0;
          await this.updateCurrentTrack();
        }
        
        return response.data;
      } catch (error) {
        console.error('Erreur lors de l\'ajout à la file d\'attente:', error);
        throw error;
      }
    },
    
    // Supprimer une musique de la file d'attente
    async removeFromQueue(queueItemId: number) {
      try {
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
      }
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
    }
  }
}); 
import { defineStore } from 'pinia';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useMusicStore = defineStore('music', {
  state: () => ({
    currentTrack: null as any,
    searchResults: [] as any[]
  }),
  
  actions: {
    // Rechercher des musiques dans la base de données
    async searchMusic(query: string) {
      try {
        const response = await axios.get(`${API_URL}/api/music`, {
          params: { search: query }
        });
        
        this.searchResults = response.data;
        return this.searchResults;
      } catch (error) {
        console.error('Erreur lors de la recherche de musiques:', error);
        return [];
      }
    },
    
    // Rechercher des musiques sur YouTube
    async searchYoutube(query: string) {
      try {
        const response = await axios.post(`${API_URL}/api/music/search`, null, {
          params: { query }
        });
        
        return response.data;
      } catch (error) {
        console.error('Erreur lors de la recherche sur YouTube:', error);
        return [];
      }
    },
    
    // Télécharger une musique depuis une URL
    async uploadMusic(data: { source_url: string }) {
      try {
        const response = await axios.post(`${API_URL}/api/music/upload`, data);
        return response.data;
      } catch (error) {
        console.error('Erreur lors du téléchargement de la musique:', error);
        throw error;
      }
    },
    
    // Définir la piste actuelle
    setCurrentTrack(track: any) {
      this.currentTrack = track;
    },
    
    // Récupérer les détails d'une musique
    async getMusicDetails(musicId: number) {
      try {
        const response = await axios.get(`${API_URL}/api/music/${musicId}`);
        return response.data;
      } catch (error) {
        console.error(`Erreur lors de la récupération des détails de la musique ${musicId}:`, error);
        throw error;
      }
    }
  }
}); 
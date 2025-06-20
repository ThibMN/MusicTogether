import { defineStore } from 'pinia';
import axios, { AxiosError } from 'axios';

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
        console.log('Recherche de musique avec la requête:', query);
        const response = await axios.get(`${API_URL}/api/music`, {
          params: { search: query }
        });
        
        console.log('Résultats de recherche:', response.data);
        this.searchResults = response.data;
        return this.searchResults;
      } catch (error) {
        console.error('Erreur lors de la recherche de musiques:', error);
        return [];
      }
    },
    
    // Rechercher des musiques sur YouTube
    async searchYouTube(query: string) {
      try {
        console.log('Recherche YouTube avec la requête:', query);
        console.log('URL de la requête:', `${API_URL}/api/music/search`);
        
        const response = await axios.get(`${API_URL}/api/music/search`, {
          params: { query }
        });
        
        console.log('Résultats de recherche YouTube:', response.data);
        return response.data;
      } catch (error: unknown) {
        console.error('Erreur lors de la recherche YouTube:', error);
        if (axios.isAxiosError(error)) {
          console.error('Détails de l\'erreur:', error.response?.data || 'Pas de données de réponse');
          console.error('Statut de l\'erreur:', error.response?.status || 'Pas de statut');
        }
        throw error;
      }
    },
    
    // Télécharger une musique depuis une URL
    async uploadMusic(data: { source_url: string }) {
      try {
        console.log('Téléchargement de musique depuis URL:', data.source_url);
        const response = await axios.post(`${API_URL}/api/music/upload`, data);
        console.log('Réponse du téléchargement:', response.data);
        return response.data;
      } catch (error) {
        console.error('Erreur détaillée lors du téléchargement de la musique:', error);
        throw error;
      }
    },
    
    // Télécharger une musique depuis un fichier local
    async uploadMusicFile(file: File) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await axios.post(`${API_URL}/api/music/upload-file`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        console.log('Réponse de l\'upload fichier:', response.data);
        return response.data;
      } catch (error) {
        console.error('Erreur lors de l\'upload du fichier audio:', error);
        throw error;
      }
    },
    
    // Récupérer les détails d'une musique
    async getMusicDetails(musicId: number) {
      try {
        console.log('Récupération des détails de la musique:', musicId);
        const response = await axios.get(`${API_URL}/api/music/${musicId}`);
        console.log('Détails de la musique récupérés:', response.data);
        return response.data;
      } catch (error) {
        console.error(`Erreur lors de la récupération des détails de la musique ${musicId}:`, error);
        throw error;
      }
    },
    
    // Mettre à jour la piste actuelle
    setCurrentTrack(track: any) {
      console.log('Mise à jour de la piste actuelle:', track);
      this.currentTrack = track;
    }
  }
}); 
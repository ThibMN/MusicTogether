<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useMusicStore } from '../stores/music';
import { useQueueStore } from '../stores/queue';
import { useRoomStore } from '../stores/room';

// Stores
const musicStore = useMusicStore();
const queueStore = useQueueStore();
const roomStore = useRoomStore();
const router = useRouter();

// État local
const searchQuery = ref('');
const isSearching = ref(false);
const searchResults = ref<any[]>([]);
const uploadUrl = ref('');
const isUploading = ref(false);
const showResults = ref(false);
const isInLocalSearch = ref(false);

// Récupérer la salle actuelle depuis le store
const currentRoom = computed(() => roomStore.currentRoom);

// Effectuer une recherche
const performSearch = async (query: string) => {
  if (!query.trim()) return;
  
  console.log('Début de la recherche pour:', query);
  isSearching.value = true;
  showResults.value = true;
  
  try {
    let results;
    
    // D'abord chercher dans la base de données locale
    isInLocalSearch.value = true;
    results = await musicStore.searchMusic(query);
    console.log('Résultats de la recherche locale:', results);
    
    // Si aucun résultat local ou peu de résultats, chercher sur YouTube
    if (!results || results.length < 5) {
      console.log('Recherche YouTube pour:', query);
      isInLocalSearch.value = false;
      try {
        const youtubeResults = await musicStore.searchYouTube(query);
        console.log('Résultats YouTube reçus:', youtubeResults);
        
        // Ajouter un indicateur pour chaque résultat YouTube
        const formattedResults = youtubeResults.map((result: any) => ({
          ...result,
          isYoutube: true,
          isLoading: false
        }));
        
        // Combiner les résultats locaux et YouTube
        if (results && results.length > 0) {
          results = [...results, ...formattedResults];
        } else {
          results = formattedResults;
        }
      } catch (youtubeError) {
        console.error('Erreur lors de la recherche YouTube:', youtubeError);
        // Continuer avec les résultats locaux seulement
      }
    }
    
    searchResults.value = results || [];
  } catch (error) {
    console.error('Erreur lors de la recherche:', error);
    searchResults.value = [];
  } finally {
    isSearching.value = false;
  }
};

// Rechercher des musiques au fur et à mesure de la saisie (avec délai)
let searchTimeout: number | null = null;
const handleSearchInput = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }
  
  searchTimeout = window.setTimeout(async () => {
    if (searchQuery.value.trim()) {
      await performSearch(searchQuery.value);
    } else {
      showResults.value = false;
      searchResults.value = [];
    }
  }, 500);
};

// Surveiller les changements dans la barre de recherche
const watchSearchQuery = () => {
  handleSearchInput();
};

// Rechercher des musiques (pour le bouton de recherche)
const searchMusic = async () => {
  await performSearch(searchQuery.value);
};

// Ajouter une musique à la file d'attente
const addToQueue = async (musicId: number) => {
  if (!currentRoom.value) return;
  
  try {
    console.log('Ajout à la file d\'attente, musicId:', musicId, 'roomId:', currentRoom.value.id);
    await queueStore.addToQueue({
      room_id: currentRoom.value.id,
      music_id: musicId
    });
    
    // Fermer les résultats de recherche
    showResults.value = false;
    searchQuery.value = '';
  } catch (error) {
    console.error('Erreur lors de l\'ajout à la file d\'attente:', error);
  }
};

// Télécharger une musique depuis une URL
const uploadMusic = async () => {
  if (!uploadUrl.value.trim() || !currentRoom.value) return;
  
  isUploading.value = true;
  try {
    console.log('Téléchargement depuis URL:', uploadUrl.value);
    const result = await musicStore.uploadMusic({
      source_url: uploadUrl.value
    });
    
    // Si le téléchargement est réussi, ajouter à la file d'attente
    if (result && result.music_id) {
      try {
        console.log('Téléchargement réussi, ajout à la file d\'attente:', result.music_id);
        await queueStore.addToQueue({
          room_id: currentRoom.value.id,
          music_id: result.music_id
        });
        
        // Réinitialiser le champ et fermer le modal
        uploadUrl.value = '';
        closeUploadModal();
        
        // Afficher un message de succès
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed bottom-4 right-4 bg-green-600 text-white p-4 rounded shadow-lg z-50';
        successMessage.textContent = 'Musique ajoutée à la file d\'attente avec succès!';
        document.body.appendChild(successMessage);
        
        // Supprimer le message après 3 secondes
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
      } catch (queueError) {
        console.error('Erreur lors de l\'ajout à la file d\'attente:', queueError);
        alert('La musique a été téléchargée mais n\'a pas pu être ajoutée à la file d\'attente: ' + 
          (queueError instanceof Error ? queueError.message : 'Erreur inconnue'));
      }
    } else {
      throw new Error('Le serveur n\'a pas retourné d\'ID de musique valide');
    }
  } catch (error) {
    console.error('Erreur lors du téléchargement:', error);
    alert('Erreur lors du téléchargement: ' + (error instanceof Error ? error.message : 'Erreur inconnue'));
  } finally {
    isUploading.value = false;
  }
};

// Télécharger une musique depuis les résultats de recherche YouTube
const downloadFromYoutube = async (result: any) => {
  if (!currentRoom.value) return;
  if (result.isLoading) return; // Éviter les clics multiples

  try {
    // Mettre à jour l'état de chargement pour ce résultat spécifique
    result.isLoading = true;
    
    console.log('Début du téléchargement depuis YouTube:', result.url);
    const response = await musicStore.uploadMusic({
      source_url: result.url
    });
    console.log('Réponse du téléchargement YouTube:', response);
    
    // Si le téléchargement retourne un music_id
    if (response && response.music_id) {
      console.log('Ajout à la file d\'attente après téléchargement YouTube:', response.music_id);
      try {
        await queueStore.addToQueue({
          room_id: currentRoom.value.id,
          music_id: response.music_id
        });
        
        // Fermer les résultats de recherche et afficher un message de succès
        showResults.value = false;
        searchQuery.value = '';
        
        const successMessage = document.createElement('div');
        successMessage.className = 'fixed bottom-4 right-4 bg-green-600 text-white p-4 rounded shadow-lg z-50';
        successMessage.textContent = 'Musique ajoutée à la file d\'attente avec succès!';
        document.body.appendChild(successMessage);
        
        // Supprimer le message après 3 secondes
        setTimeout(() => {
          document.body.removeChild(successMessage);
        }, 3000);
      } catch (queueError) {
        console.error('Erreur lors de l\'ajout à la file d\'attente:', queueError);
        alert('La musique a été téléchargée mais n\'a pas pu être ajoutée à la file d\'attente: ' + 
          (queueError instanceof Error ? queueError.message : 'Erreur inconnue'));
      }
    } else {
      throw new Error('Le serveur n\'a pas retourné d\'ID de musique valide');
    }
  } catch (error) {
    console.error('Erreur lors du téléchargement depuis YouTube:', error);
    alert('Erreur lors du téléchargement: ' + (error instanceof Error ? error.message : 'Erreur inconnue'));
  } finally {
    // Réinitialiser l'état de chargement pour ce résultat
    result.isLoading = false;
  }
};

// Formater la durée (MM:SS)
const formatTime = (seconds: number): string => {
  if (!seconds) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
};

// Fermer les résultats de recherche en cliquant à l'extérieur
const closeResults = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (!target.closest('.search-container')) {
    showResults.value = false;
  }
};

// Ajouter l'écouteur d'événements pour fermer les résultats
onMounted(() => {
  document.addEventListener('click', closeResults);
});

// Nettoyer l'écouteur d'événements
onUnmounted(() => {
  document.removeEventListener('click', closeResults);
});

const openUploadModal = () => {
  const modal = document.getElementById('uploadModal');
  if (modal) {
    modal.classList.remove('hidden');
  }
};

const closeUploadModal = () => {
  const modal = document.getElementById('uploadModal');
  if (modal) {
    modal.classList.add('hidden');
  }
};
</script>

<template>
  <div class="search-container relative">
    <!-- Barre de recherche -->
    <div class="flex">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Rechercher une musique..."
        class="flex-1 p-3 rounded-l bg-gray-700 text-white focus:outline-none"
        @input="watchSearchQuery"
      />
      <button
        @click="searchMusic"
        class="bg-blue-600 hover:bg-blue-700 px-4 py-2"
        :disabled="isSearching"
      >
        {{ isSearching ? 'Recherche...' : 'Rechercher' }}
      </button>
      
      <!-- Bouton d'upload -->
      <button
        class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-r flex items-center"
        @click="openUploadModal"
      >
        <span>Upload</span>
      </button>
    </div>
    
    <!-- Indicateur de recherche -->
    <div v-if="isSearching" class="absolute top-full left-0 right-0 mt-1 p-2 text-center text-white bg-gray-800 rounded z-50">
      Recherche en cours...
    </div>
    
    <!-- Résultats de recherche -->
    <div
      v-if="showResults && searchResults.length > 0"
      class="absolute z-50 left-0 right-0 mt-1 bg-gray-800 rounded shadow-lg max-h-96 overflow-y-auto search-results"
    >
      <!-- Résultats locaux -->
      <div
        v-for="result in searchResults"
        :key="result.id || result.url"
        class="p-3 border-b border-gray-700 hover:bg-gray-700 cursor-pointer"
      >
        <div class="flex items-center">
          <!-- Miniature -->
          <div class="w-16 h-12 bg-gray-700 rounded mr-3 flex-shrink-0 overflow-hidden">
            <img
              v-if="result.cover_path || result.thumbnail"
              :src="result.isYoutube ? result.thumbnail : `http://localhost:8000${result.cover_path}`"
              alt="Thumbnail"
              class="w-full h-full object-cover"
            />
            <div v-else class="w-full h-full flex items-center justify-center text-gray-500">
              <span>♪</span>
            </div>
          </div>
          
          <!-- Informations sur la piste -->
          <div class="flex-1">
            <div class="font-medium truncate">{{ result.title }}</div>
            <div class="text-sm text-gray-400 truncate">
              {{ result.artist || result.channel }}
              <span v-if="result.isYoutube" class="ml-2 px-1 py-0.5 bg-red-600 rounded text-xs">YouTube</span>
            </div>
            <div class="text-xs text-gray-500">
              {{ formatTime(result.duration) }}
              <span v-if="result.isYoutube && result.view_count">
                • {{ result.view_count.toLocaleString() }} vues
              </span>
            </div>
          </div>
          
          <!-- Bouton d'action -->
          <button 
            v-if="result.isYoutube"
            @click.stop="downloadFromYoutube(result)"
            class="ml-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
            :disabled="result.isLoading"
          >
            {{ result.isLoading ? 'En cours...' : 'Télécharger' }}
          </button>
          <button
            v-else
            @click.stop="addToQueue(result.id)"
            class="ml-2 px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-sm"
          >
            Ajouter
          </button>
        </div>
      </div>
    </div>
    
    <!-- Message si aucun résultat -->
    <div
      v-if="showResults && searchResults.length === 0 && !isSearching"
      class="absolute z-50 left-0 right-0 mt-1 bg-gray-800 rounded shadow-lg p-4 text-center text-gray-500"
    >
      Aucun résultat trouvé
    </div>
  </div>
  
  <!-- Modal d'upload -->
  <div id="uploadModal" class="hidden fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 max-w-md w-full relative">
      <h3 class="text-xl mb-4">Télécharger une musique</h3>
      
      <button 
        class="absolute top-4 right-4 text-gray-400 hover:text-white"
        @click="closeUploadModal"
      >
        &times;
      </button>
      
      <div class="mb-4">
        <label class="block mb-2">URL YouTube ou SoundCloud:</label>
        <input 
          v-model="uploadUrl"
          type="text"
          placeholder="https://..."
          class="w-full p-2 bg-gray-700 rounded"
          :disabled="isUploading"
        />
      </div>
      
      <button
        @click="uploadMusic"
        class="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded"
        :disabled="isUploading || !uploadUrl.trim()"
      >
        {{ isUploading ? 'Téléchargement en cours...' : 'Télécharger' }}
      </button>
      
      <div class="mt-4 text-sm text-gray-400">
        Le téléchargement peut prendre quelques instants selon la taille du fichier et la vitesse de connexion.
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-results {
  position: fixed;
  top: auto;
  max-width: 100%;
  width: 100%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
}

@media (min-width: 768px) {
  .search-results {
    max-width: 60%;
    width: 60%;
    left: 50%;
    transform: translateX(-50%);
  }
}
</style> 
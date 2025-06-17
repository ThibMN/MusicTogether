<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useMusicStore } from '../stores/music';
import { useQueueStore } from '../stores/queue';
import { useRoomStore } from '../stores/room';

// Stores
const musicStore = useMusicStore();
const queueStore = useQueueStore();
const roomStore = useRoomStore();

// État local
const searchQuery = ref('');
const isSearching = ref(false);
const searchResults = ref<any[]>([]);
const showResults = ref(false);
const uploadUrl = ref('');
const isUploading = ref(false);
const searchTimeout = ref<number | null>(null);
const loadingItems = ref<{[key: string]: boolean}>({});

// Salle actuelle
const currentRoom = computed(() => roomStore.currentRoom);

// Rechercher des musiques en temps réel
watch(searchQuery, (newQuery) => {
  // Annuler la recherche précédente
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value);
  }
  
  // Si la requête est vide, masquer les résultats
  if (!newQuery.trim()) {
    showResults.value = false;
    searchResults.value = [];
    return;
  }
  
  // Attendre que l'utilisateur arrête de taper
  searchTimeout.value = setTimeout(async () => {
    await performSearch(newQuery);
  }, 300) as unknown as number;
});

// Effectuer la recherche
const performSearch = async (query: string) => {
  if (!query.trim()) return;
  
  isSearching.value = true;
  try {
    const results = await musicStore.searchYoutube(query);
    // Réinitialiser l'état de chargement pour chaque résultat
    searchResults.value = results.map((result: any) => ({
      ...result,
      isLoading: false
    }));
    showResults.value = true;
  } catch (error) {
    console.error('Erreur lors de la recherche:', error);
  } finally {
    isSearching.value = false;
  }
};

// Rechercher des musiques (pour le bouton de recherche)
const searchMusic = async () => {
  await performSearch(searchQuery.value);
};

// Ajouter une musique à la file d'attente
const addToQueue = async (musicId: number) => {
  if (!currentRoom.value) return;
  
  try {
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
    const result = await musicStore.uploadMusic({
      source_url: uploadUrl.value
    });
    
    // Si le téléchargement est réussi, ajouter à la file d'attente
    if (result && result.music_id) {
      await queueStore.addToQueue({
        room_id: currentRoom.value.id,
        music_id: result.music_id
      });
    }
    
    // Réinitialiser le champ et fermer le modal
    uploadUrl.value = '';
    document.getElementById('uploadModal')?.classList.add('hidden');
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
    
    console.log('Début du téléchargement:', result.url);
    const uploadResult = await musicStore.uploadMusic({
      source_url: result.url
    });
    console.log('Résultat du téléchargement:', uploadResult);
    
    // Si le téléchargement est réussi, ajouter à la file d'attente
    if (uploadResult && uploadResult.music_id) {
      console.log('Ajout à la file d\'attente:', uploadResult.music_id);
      await queueStore.addToQueue({
        room_id: currentRoom.value.id,
        music_id: uploadResult.music_id
      });
      
      // Fermer les résultats de recherche
      showResults.value = false;
      searchQuery.value = '';
    } else {
      console.error('Téléchargement réussi mais aucun music_id retourné');
      alert('Le téléchargement a réussi mais la musique n\'a pas pu être ajoutée à la file d\'attente.');
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
        @click="() => document.getElementById('uploadModal')?.classList.remove('hidden')"
      >
        <span>Upload</span>
      </button>
    </div>
    
    <!-- Indicateur de recherche -->
    <div v-if="isSearching" class="absolute top-full left-0 right-0 mt-1 p-2 text-center text-white bg-gray-800 rounded">
      Recherche en cours...
    </div>
    
    <!-- Résultats de recherche YouTube -->
    <div
      v-if="showResults && searchResults.length > 0"
      class="absolute z-50 left-0 right-0 mt-1 bg-gray-800 rounded shadow-lg max-h-96 overflow-y-auto search-results"
    >
      <div
        v-for="result in searchResults"
        :key="result.id"
        class="p-3 border-b border-gray-700 hover:bg-gray-700 cursor-pointer"
      >
        <div class="flex items-center">
          <!-- Miniature -->
          <div class="w-16 h-12 bg-gray-700 rounded mr-3 flex-shrink-0 overflow-hidden">
            <img
              v-if="result.thumbnail"
              :src="result.thumbnail"
              alt="Thumbnail"
              class="w-full h-full object-cover"
            />
            <div v-else class="w-full h-full flex items-center justify-center text-gray-500">
              <span>♪</span>
            </div>
          </div>
          
          <!-- Informations sur la vidéo -->
          <div class="flex-1">
            <div class="font-medium truncate">{{ result.title }}</div>
            <div class="text-sm text-gray-400 truncate">{{ result.channel }}</div>
            <div class="text-xs text-gray-500">
              {{ formatTime(result.duration) }} • {{ result.view_count ? `${result.view_count.toLocaleString()} vues` : '' }}
            </div>
          </div>
          
          <!-- Bouton de téléchargement -->
          <button 
            @click.stop="downloadFromYoutube(result)"
            class="ml-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
            :disabled="result.isLoading"
          >
            {{ result.isLoading ? 'En cours...' : 'Télécharger' }}
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
    
    <!-- Modal d'upload -->
    <div
      id="uploadModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 hidden"
    >
      <div class="bg-gray-800 p-6 rounded-lg shadow-lg max-w-md w-full">
        <h2 class="text-xl font-bold mb-4">Ajouter une musique</h2>
        
        <div class="mb-4">
          <label class="block text-sm font-medium mb-2">URL (YouTube, SoundCloud, etc.)</label>
          <input
            v-model="uploadUrl"
            type="text"
            placeholder="https://..."
            class="w-full p-3 rounded bg-gray-700 text-white focus:outline-none"
            @keyup.enter="uploadMusic"
          />
        </div>
        
        <div class="flex justify-end space-x-3">
          <button
            @click="() => document.getElementById('uploadModal')?.classList.add('hidden')"
            class="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600"
          >
            Annuler
          </button>
          <button
            @click="uploadMusic"
            class="px-4 py-2 rounded bg-green-600 hover:bg-green-700"
            :disabled="isUploading"
          >
            {{ isUploading ? 'Téléchargement...' : 'Ajouter' }}
          </button>
        </div>
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
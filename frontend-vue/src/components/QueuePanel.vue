<script setup lang="ts">
import { computed } from 'vue';
import { useQueueStore } from '../stores/queue';
import { useMusicStore } from '../stores/music';
import { useRoomStore } from '../stores/room';

// Stores
const queueStore = useQueueStore();
const musicStore = useMusicStore();
const roomStore = useRoomStore();

// File d'attente
const queueItems = computed(() => queueStore.queueItems);

// Piste actuelle
const currentTrack = computed(() => musicStore.currentTrack);

// Jouer une piste spécifique
const playTrack = (trackId: number) => {
  queueStore.playTrack(trackId);
};

// Supprimer une piste de la file d'attente
const removeFromQueue = async (queueItemId: number) => {
  await queueStore.removeFromQueue(queueItemId);
};

// Réorganiser la file d'attente (drag and drop)
const onDragStart = (event: DragEvent, itemId: number) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('text/plain', itemId.toString());
    event.dataTransfer.effectAllowed = 'move';
  }
};

const onDragOver = (event: DragEvent) => {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move';
  }
};

const onDrop = async (event: DragEvent, targetItemId: number) => {
  event.preventDefault();
  if (!event.dataTransfer) return;
  
  const sourceItemId = parseInt(event.dataTransfer.getData('text/plain'), 10);
  if (sourceItemId !== targetItemId) {
    await queueStore.reorderQueue(sourceItemId, targetItemId);
  }
};
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="p-3 border-b border-gray-700">
      <h2 class="text-lg font-semibold">File d'attente</h2>
    </div>
    
    <!-- Liste des pistes dans la file d'attente -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="queueItems.length === 0" class="p-4 text-center text-gray-500">
        <p>La file d'attente est vide</p>
        <p class="text-sm mt-2">Utilisez la barre de recherche pour ajouter des musiques</p>
      </div>
      
      <div 
        v-for="item in queueItems" 
        :key="item.id"
        class="p-3 border-b border-gray-700 flex items-center hover:bg-gray-800 cursor-pointer"
        :class="{ 'bg-gray-800': currentTrack?.id === item.music.id }"
        draggable="true"
        @dragstart="onDragStart($event, item.id)"
        @dragover="onDragOver($event)"
        @drop="onDrop($event, item.id)"
        @click="playTrack(item.music.id)"
      >
        <!-- Cover miniature -->
        <div class="w-10 h-10 bg-gray-700 rounded mr-3 flex-shrink-0 overflow-hidden">
          <img 
            v-if="item.music.cover_path" 
            :src="`http://localhost:8000${item.music.cover_path}`" 
            alt="Cover"
            class="w-full h-full object-cover"
          />
        </div>
        
        <!-- Informations sur la piste -->
        <div class="flex-1 min-w-0">
          <div class="font-medium truncate">{{ item.music.title }}</div>
          <div class="text-sm text-gray-400 truncate">{{ item.music.artist }}</div>
        </div>
        
        <!-- Durée -->
        <div class="text-sm text-gray-400 ml-2">
          {{ formatTime(item.music.duration) }}
        </div>
        
        <!-- Bouton supprimer -->
        <button 
          @click.stop="removeFromQueue(item.id)"
          class="ml-2 text-gray-400 hover:text-red-500"
        >
          <span class="text-lg">×</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// Formatage du temps (MM:SS)
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}
</script> 
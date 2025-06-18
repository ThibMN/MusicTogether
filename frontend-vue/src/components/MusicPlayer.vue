<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useMusicStore } from '../stores/music';
import { useQueueStore } from '../stores/queue';
import { useRoomStore } from '../stores/room';

// Stores
const musicStore = useMusicStore();
const queueStore = useQueueStore();
const roomStore = useRoomStore();

// Références
const audioPlayer = ref<HTMLAudioElement | null>(null);
const audioElement = ref<HTMLAudioElement | null>(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const volume = ref(0.7);
const visualizer = ref<HTMLCanvasElement | null>(null);
const controlsLocked = ref(false);
const forceSync = ref(false);

// Musique actuelle
const currentTrack = computed(() => musicStore.currentTrack);

// URL audio
const audioUrl = computed(() => {
  if (!currentTrack.value) return '';
  return `http://localhost:8000/api/music/${currentTrack.value.id}/stream`;
});

// Progression de la lecture (0-100)
const progress = computed(() => {
  if (duration.value === 0) return 0;
  return (currentTime.value / duration.value) * 100;
});

// Formatage du temps (MM:SS)
const formatTime = (seconds: number) => {
  if (isNaN(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
};

// Lecture/Pause
const togglePlay = () => {
  if (!audioElement.value || !currentTrack.value || controlsLocked.value) return;
  
  if (isPlaying.value) {
    console.log(`Pause manuelle à ${audioElement.value.currentTime}`);
    audioElement.value.pause();
    
    // Envoyer l'état de pause aux autres utilisateurs
    roomStore.sendPlaybackUpdate({
      type: 'pause',
      trackId: currentTrack.value.id,
      position: audioElement.value.currentTime,
      isPlaying: false
    });
  } else {
    console.log(`Reprise manuelle à ${audioElement.value.currentTime}`);
    audioElement.value.play();
    
    // Envoyer l'état de lecture aux autres utilisateurs
    roomStore.sendPlaybackUpdate({
      type: 'play',
      trackId: currentTrack.value.id,
      position: audioElement.value.currentTime,
      isPlaying: true
    });
  }
};

// Passer à la musique suivante
const nextTrack = async () => {
  if (controlsLocked.value) return;
  
  await queueStore.playNextTrack();
  
  // Annoncer le changement de piste aux autres utilisateurs
  if (currentTrack.value) {
    roomStore.sendPlaybackUpdate({
      type: 'track_change',
      trackId: currentTrack.value.id,
      position: 0,
      isPlaying: true
    });
  }
};

// Revenir à la musique précédente
const prevTrack = async () => {
  if (controlsLocked.value) return;
  
  // Revenir au début de la piste si on a dépassé les 3 secondes
  if (audioElement.value && audioElement.value.currentTime > 3) {
    audioElement.value.currentTime = 0;
    currentTime.value = 0;
    
    // Annoncer le changement de position aux autres
    roomStore.sendPlaybackUpdate({
      type: 'seek',
      trackId: currentTrack.value?.id,
      position: 0,
      isPlaying: isPlaying.value
    });
    
    return;
  }
  
  // Sinon, revenir à la piste précédente
  await queueStore.playPreviousTrack();
  
  // Annoncer le changement de piste aux autres utilisateurs
  if (currentTrack.value) {
    roomStore.sendPlaybackUpdate({
      type: 'track_change',
      trackId: currentTrack.value.id,
      position: 0,
      isPlaying: true
    });
  }
};

// Changer la position de lecture
const seekTo = (position: number) => {
  if (!audioElement.value || controlsLocked.value) return;
  
  console.log(`Déplacement manuel à ${position}`);
  audioElement.value.currentTime = position;
  currentTime.value = position;
  
  // Envoyer la mise à jour de position aux autres utilisateurs
  roomStore.sendPlaybackUpdate({
    type: 'seek',
    trackId: currentTrack.value?.id,
    position: position,
    isPlaying: isPlaying.value
  });
};

// Changer le volume
const changeVolume = (value: number) => {
  volume.value = value;
  if (audioElement.value) {
    audioElement.value.volume = value;
  }
};

// Fonction pour gérer l'événement d'actualisation du temps
const handleTimeUpdate = () => {
  if (!audioElement.value) return;
  currentTime.value = audioElement.value.currentTime;
};

// Fonction pour gérer l'événement de fin de lecture
const handleEnded = () => {
  console.log("Lecture terminée, passage à la piste suivante");
  nextTrack();
};

// Fonction pour gérer l'événement de chargement
const handleLoadedMetadata = () => {
  if (!audioElement.value) return;
  console.log(`Métadonnées chargées, durée: ${audioElement.value.duration}`);
  duration.value = audioElement.value.duration;
};

// Fonction pour gérer l'événement de début de lecture
const handlePlay = () => {
  console.log("Lecture démarrée");
  isPlaying.value = true;
};

// Fonction pour gérer l'événement de pause
const handlePause = () => {
  console.log("Lecture en pause");
  isPlaying.value = false;
};

// Gérer les mises à jour de lecture provenant d'autres utilisateurs
const handlePlaybackUpdate = async (update: any) => {
  console.log("Message WebSocket reçu:", update);
  
  // Si nous n'avons pas de lecteur, ignorons la plupart des messages
  if (!audioElement.value) {
    console.log("Pas de lecteur audio disponible");
    return;
  }
  
  // Ignorer les messages provenant de nous-mêmes (en utilisant l'ID client)
  if (update.client_id && update.client_id === roomStore.clientId) {
    console.log("Message ignoré (provient de nous-mêmes)");
    return;
  }
  
  // Verrouiller temporairement les contrôles pour éviter les boucles
  controlsLocked.value = true;
  
  try {
    // CHANGEMENT DE PISTE
    if (update.type === 'track_change' && update.trackId !== undefined) {
      console.log(`Réception d'un changement de piste vers ${update.trackId}`);
      // Vérifier si c'est une piste différente de celle actuellement jouée
      if (!currentTrack.value || update.trackId !== currentTrack.value.id) {
        // Charger la nouvelle piste dans la file d'attente
        console.log(`Chargement de la piste ${update.trackId}`);
        await queueStore.playTrack(update.trackId);
        
        // La suite sera gérée via le watcher de currentTrack.value
        return;
      }
    }
    
    // SYNCHRONISATION DE POSITION
    if (update.position !== undefined) {
      const currentPos = audioElement.value.currentTime;
      // Seulement mettre à jour si la différence est significative
      if (Math.abs(currentPos - update.position) > 1.0 || forceSync.value) {
        console.log(`Synchronisation de position: ${currentPos} -> ${update.position}`);
        audioElement.value.currentTime = update.position;
        currentTime.value = update.position;
        forceSync.value = false;
      }
    }
    
    // LECTURE/PAUSE
    if (update.type === 'play' && !isPlaying.value) {
      console.log("Démarrage de la lecture suite à un message externe");
      audioElement.value.play();
    } else if (update.type === 'pause' && isPlaying.value) {
      console.log("Mise en pause suite à un message externe");
      audioElement.value.pause();
    }
  } finally {
    // Déverrouiller les contrôles
    setTimeout(() => {
      controlsLocked.value = false;
    }, 500);
  }
};

// Mettre à jour les autres utilisateurs sur l'état de la lecture régulièrement
let syncInterval: number | null = null;

const startSyncInterval = () => {
  if (syncInterval) return;
  
  syncInterval = window.setInterval(() => {
    if (audioElement.value && currentTrack.value) {
      const currentPos = audioElement.value.currentTime;
      console.log(`Synchronisation périodique: trackId=${currentTrack.value.id}, position=${currentPos}, lecture=${isPlaying.value}`);
      
      roomStore.sendPlaybackUpdate({
        type: 'sync',
        trackId: currentTrack.value.id,
        position: currentPos,
        isPlaying: isPlaying.value
      });
    }
  }, 2000); // Sync toutes les 2 secondes
};

const stopSyncInterval = () => {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
};

// Surveiller les changements de piste
watch(() => currentTrack.value, (newTrack) => {
  if (newTrack) {
    // Forcer la synchronisation au changement de piste
    forceSync.value = true;
    console.log(`Nouvelle piste chargée: ${newTrack.title}`);
  }
});

// Surveiller l'URL audio
watch(audioUrl, (newUrl) => {
  if (newUrl && audioElement.value) {
    console.log(`Chargement de l'URL audio: ${newUrl}`);
    audioElement.value.src = newUrl;
    audioElement.value.load();
    
    // Démarrer la lecture automatiquement après chargement
    audioElement.value.play().catch(err => {
      console.error('Erreur lors du démarrage automatique de la lecture:', err);
    });
  }
});

// Initialisation et nettoyage
onMounted(() => {
  // Créer l'élément audio
  audioElement.value = new Audio();
  audioElement.value.volume = volume.value;
  
  // Ajouter les écouteurs d'événements
  audioElement.value.addEventListener('timeupdate', handleTimeUpdate);
  audioElement.value.addEventListener('ended', handleEnded);
  audioElement.value.addEventListener('loadedmetadata', handleLoadedMetadata);
  audioElement.value.addEventListener('play', handlePlay);
  audioElement.value.addEventListener('pause', handlePause);
  
  // Écouter les mises à jour de lecture
  roomStore.onPlaybackUpdate(handlePlaybackUpdate);
  
  // Initialiser le lecteur si une piste est déjà chargée
  if (currentTrack.value && audioUrl.value) {
    audioElement.value.src = audioUrl.value;
    audioElement.value.load();
  }
  
  // Démarrer la synchronisation périodique
  startSyncInterval();
  
  console.log("Lecteur audio initialisé");
});

onUnmounted(() => {
  // Nettoyer les écouteurs d'événements
  if (audioElement.value) {
    audioElement.value.removeEventListener('timeupdate', handleTimeUpdate);
    audioElement.value.removeEventListener('ended', handleEnded);
    audioElement.value.removeEventListener('loadedmetadata', handleLoadedMetadata);
    audioElement.value.removeEventListener('play', handlePlay);
    audioElement.value.removeEventListener('pause', handlePause);
    
    // Arrêter la lecture
    audioElement.value.pause();
    audioElement.value.src = '';
  }
  
  // Arrêter la synchronisation
  stopSyncInterval();
  
  console.log("Lecteur audio nettoyé");
});
</script>

<template>
  <div class="flex flex-col items-center w-full h-full p-6 overflow-y-auto">
    <!-- Cover -->
    <div 
      class="w-80 h-80 bg-gray-800 rounded-lg mb-6 flex items-center justify-center overflow-hidden shadow-lg transition-all duration-500 ease-in-out"
      :class="{ 'animate-pulse': !currentTrack, 'scale-105': isPlaying }"
    >
      <img 
        v-if="currentTrack?.cover_path" 
        :src="`http://localhost:8000${currentTrack.cover_path}`" 
        alt="Album cover"
        class="w-full h-full object-cover transition-opacity duration-300"
      />
      <div v-else class="text-gray-500 text-center">
        <span class="text-6xl">♪</span>
      </div>
    </div>
    
    <!-- Informations sur la piste -->
    <div class="text-center mb-6 w-full">
      <h2 class="text-xl font-bold truncate">
        {{ currentTrack?.title || 'Titre' }}
      </h2>
      <p class="text-gray-400 truncate">
        {{ currentTrack?.artist || 'Auteur' }}
      </p>
    </div>
    
    <!-- Contrôles de lecture -->
    <div class="flex items-center justify-center space-x-6 mb-4">
      <button 
        @click="prevTrack"
        class="text-white hover:text-blue-400 transition-colors"
        :disabled="controlsLocked"
      >
        <span class="text-2xl">⏮</span>
      </button>
      
      <button 
        @click="togglePlay"
        class="bg-blue-600 hover:bg-blue-700 rounded-full w-12 h-12 flex items-center justify-center"
        :disabled="controlsLocked"
      >
        <span class="text-2xl">{{ isPlaying ? '⏸' : '▶' }}</span>
      </button>
      
      <button 
        @click="nextTrack"
        class="text-white hover:text-blue-400 transition-colors"
        :disabled="controlsLocked"
      >
        <span class="text-2xl">⏭</span>
      </button>
    </div>
    
    <!-- Barre de progression -->
    <div class="w-full mb-2 flex items-center space-x-2">
      <span class="text-xs text-gray-400">{{ formatTime(currentTime) }}</span>
      
      <div 
        class="flex-1 h-1 bg-gray-700 rounded overflow-hidden cursor-pointer"
        @click="(e) => {
          const rect = e.target.getBoundingClientRect();
          const percent = (e.clientX - rect.left) / rect.width;
          seekTo(percent * duration);
        }"
      >
        <div 
          class="h-full bg-blue-600"
          :style="{ width: `${progress}%` }"
        ></div>
      </div>
      
      <span class="text-xs text-gray-400">{{ formatTime(duration) }}</span>
    </div>
    
    <!-- Contrôle du volume -->
    <div class="w-full flex items-center space-x-2">
      <span class="text-xs text-gray-400">volume</span>
      <input 
        type="range"
        min="0"
        max="1"
        step="0.01"
        v-model="volume"
        @input="changeVolume(parseFloat(($event.target as HTMLInputElement).value))"
        class="flex-1 h-1 bg-gray-700 rounded appearance-none"
      />
    </div>
    
    <!-- Élément audio invisible -->
    <audio ref="audioPlayer" style="display: none;"></audio>
  </div>
</template> 
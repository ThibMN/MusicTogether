<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { Howl } from 'howler';
import { useMusicStore } from '../stores/music';
import { useQueueStore } from '../stores/queue';
import { useRoomStore } from '../stores/room';

// Stores
const musicStore = useMusicStore();
const queueStore = useQueueStore();
const roomStore = useRoomStore();

// Références
const audioPlayer = ref<Howl | null>(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const volume = ref(0.7);
const visualizer = ref<HTMLCanvasElement | null>(null);

// Musique actuelle
const currentTrack = computed(() => musicStore.currentTrack);

// Progression de la lecture (0-100)
const progress = computed(() => {
  if (duration.value === 0) return 0;
  return (currentTime.value / duration.value) * 100;
});

// Formatage du temps (MM:SS)
const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
};

// Lecture/Pause
const togglePlay = () => {
  if (!audioPlayer.value || !currentTrack.value) return;
  
  if (isPlaying.value) {
    audioPlayer.value.pause();
    isPlaying.value = false;
    
    // Envoyer l'état de pause aux autres utilisateurs
    roomStore.sendPlaybackUpdate({
      type: 'pause',
      position: currentTime.value
    });
  } else {
    audioPlayer.value.play();
    isPlaying.value = true;
    
    // Envoyer l'état de lecture aux autres utilisateurs
    roomStore.sendPlaybackUpdate({
      type: 'play',
      position: currentTime.value
    });
  }
};

// Passer à la musique suivante
const nextTrack = async () => {
  await queueStore.playNextTrack();
};

// Revenir à la musique précédente
const prevTrack = () => {
  // Revenir au début de la piste si on a dépassé les 3 secondes
  if (currentTime.value > 3) {
    seekTo(0);
    return;
  }
  
  // Sinon, revenir à la piste précédente
  queueStore.playPreviousTrack();
};

// Changer la position de lecture
const seekTo = (position: number) => {
  if (!audioPlayer.value) return;
  
  audioPlayer.value.seek(position);
  currentTime.value = position;
  
  // Envoyer la mise à jour de position aux autres utilisateurs
  roomStore.sendPlaybackUpdate({
    type: isPlaying.value ? 'play' : 'pause',
    position: position
  });
};

// Changer le volume
const changeVolume = (value: number) => {
  volume.value = value;
  if (audioPlayer.value) {
    audioPlayer.value.volume(value);
  }
};

// Initialiser le lecteur audio
const initializeAudio = () => {
  if (!currentTrack.value) return;
  
  // Nettoyer l'ancien lecteur
  if (audioPlayer.value) {
    audioPlayer.value.unload();
  }
  
  // Créer un nouveau lecteur
  audioPlayer.value = new Howl({
    src: [`http://localhost:8000/api/music/${currentTrack.value.id}/stream`],
    html5: true,
    volume: volume.value,
    onplay: () => {
      isPlaying.value = true;
      startTimeUpdate();
    },
    onpause: () => {
      isPlaying.value = false;
      stopTimeUpdate();
    },
    onend: () => {
      isPlaying.value = false;
      nextTrack();
    },
    onload: () => {
      duration.value = audioPlayer.value?.duration() || 0;
    },
    onloaderror: (id, error) => {
      console.error('Erreur de chargement audio:', error);
    }
  });
};

// Mettre à jour le temps de lecture
let timeUpdateInterval: number | null = null;

const startTimeUpdate = () => {
  if (timeUpdateInterval) return;
  
  timeUpdateInterval = window.setInterval(() => {
    if (audioPlayer.value && isPlaying.value) {
      currentTime.value = audioPlayer.value.seek();
    }
  }, 1000);
};

const stopTimeUpdate = () => {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
    timeUpdateInterval = null;
  }
};

// Gérer les mises à jour de lecture provenant d'autres utilisateurs
const handlePlaybackUpdate = (update: any) => {
  if (!audioPlayer.value) return;
  
  // Mettre à jour la position
  if (update.position !== undefined) {
    audioPlayer.value.seek(update.position);
    currentTime.value = update.position;
  }
  
  // Gérer la lecture/pause
  if (update.type === 'play' && !isPlaying.value) {
    audioPlayer.value.play();
    isPlaying.value = true;
  } else if (update.type === 'pause' && isPlaying.value) {
    audioPlayer.value.pause();
    isPlaying.value = false;
  }
};

// Surveiller les changements de piste
watch(() => currentTrack.value, (newTrack) => {
  if (newTrack) {
    initializeAudio();
    // Démarrer la lecture automatiquement
    if (audioPlayer.value) {
      audioPlayer.value.play();
    }
  }
});

// Initialisation et nettoyage
onMounted(() => {
  // Écouter les mises à jour de lecture
  roomStore.onPlaybackUpdate(handlePlaybackUpdate);
  
  // Initialiser le lecteur si une piste est déjà chargée
  if (currentTrack.value) {
    initializeAudio();
  }
});

onUnmounted(() => {
  // Nettoyer le lecteur audio
  if (audioPlayer.value) {
    audioPlayer.value.unload();
  }
  
  // Arrêter la mise à jour du temps
  stopTimeUpdate();
});
</script>

<template>
  <div class="flex flex-col items-center w-full h-full p-6 overflow-y-auto">
    <!-- Cover -->
    <div 
      class="w-64 h-64 bg-gray-800 rounded-lg mb-6 flex items-center justify-center overflow-hidden"
      :class="{ 'animate-pulse': !currentTrack }"
    >
      <img 
        v-if="currentTrack?.cover_path" 
        :src="`http://localhost:8000${currentTrack.cover_path}`" 
        alt="Album cover"
        class="w-full h-full object-cover"
      />
      <div v-else class="text-gray-500 text-center">
        <span class="text-4xl">♪</span>
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
      >
        <span class="text-2xl">⏮</span>
      </button>
      
      <button 
        @click="togglePlay"
        class="bg-blue-600 hover:bg-blue-700 rounded-full w-12 h-12 flex items-center justify-center"
      >
        <span class="text-2xl">{{ isPlaying ? '⏸' : '▶' }}</span>
      </button>
      
      <button 
        @click="nextTrack"
        class="text-white hover:text-blue-400 transition-colors"
      >
        <span class="text-2xl">⏭</span>
      </button>
    </div>
    
    <!-- Barre de progression -->
    <div class="w-full mb-2 flex items-center space-x-2">
      <span class="text-xs text-gray-400">{{ formatTime(currentTime) }}</span>
      
      <div class="flex-1 h-1 bg-gray-700 rounded overflow-hidden">
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
  </div>
</template> 
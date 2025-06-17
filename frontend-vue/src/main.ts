import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import App from './App.vue'
import './style.css'
import { useAuthStore } from './stores/auth'
// import Cookies from 'js-cookie' // Temporairement commenté
import router from './router'

// Configuration d'Axios pour le debug
axios.interceptors.request.use((request: AxiosRequestConfig) => {
  console.log('Axios Request:', request.method, request.url);
  return request;
}, (error: AxiosError) => {
  console.error('Axios Request Error:', error);
  return Promise.reject(error);
});

axios.interceptors.response.use((response: AxiosResponse) => {
  console.log('Axios Response:', response.status, response.config.url);
  return response;
}, (error: AxiosError) => {
  console.error('Axios Response Error:', error.message, error.response?.status, error.config?.url);
  return Promise.reject(error);
});

// Création de l'application
const app = createApp(App)

// Utilisation de Pinia et Vue Router
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Afficher les erreurs de montage
app.config.errorHandler = (err, instance, info) => {
  console.error('Vue Error:', err)
  console.error('Error Info:', info)
}

// Montage de l'application
app.mount('#app')

// Stocker une référence au store d'authentification
let _authStore: any = null;

// Fonction pour accéder au store d'authentification
const getAuthStore = () => {
  if (!_authStore) {
    _authStore = useAuthStore();
  }
  return _authStore;
}

// Initialiser l'écouteur global pour les messages d'authentification
// Cela permet de recevoir les messages même si l'utilisateur est sur n'importe quelle page
window.addEventListener('message', (event) => {
  console.log('🔔 Message global reçu:', event.data);
  
  if (event.data && event.data.type === 'auth_success' && event.data.data) {
    console.log('🎯 Message d\'authentification reçu globalement:', event.data);
    
    try {
      // Récupérer le store d'authentification et mettre à jour les données utilisateur
      const authStore = getAuthStore();
      authStore.setUser(event.data.data);
      
      console.log('✅ Utilisateur authentifié:', authStore.user?.username);
      
      // Vérifier s'il y a une redirection en attente
      const redirectPath = localStorage.getItem('redirect_after_login');
      if (redirectPath) {
        localStorage.removeItem('redirect_after_login');
        router.push(redirectPath);
      }
      
      // Forcer la mise à jour de la vue si nécessaire
      setTimeout(() => {
        console.log('État après authentification:', {
          user: authStore.user,
          isAuthenticated: authStore.isAuthenticated
        });
      }, 100);
      
    } catch (error) {
      console.error('❌ Erreur lors du traitement du message d\'authentification:', error);
    }
  }
});

// Pour debug dans la console
window.authDebug = {
  getAuthState: () => {
    const authStore = getAuthStore();
    return {
      user: authStore.user,
      isAuthenticated: authStore.isAuthenticated,
      // cookie: Cookies.get('auth_user') // Temporairement commenté
    };
  },
  forceUpdate: () => {
    const authStore = getAuthStore();
    // Forcer une mise à jour mineure de l'utilisateur pour déclencher la réactivité
    if (authStore.user) {
      authStore.setUser({
        ...authStore.user,
        lastUpdated: new Date().toISOString()
      });
    }
    return 'État d\'authentification mis à jour';
  }
};

// Debug
console.log('Main.ts executed, global auth listener registered');

// Déclarations pour TypeScript
declare global {
  interface Window {
    authDebug: {
      getAuthState: () => any;
      forceUpdate: () => string;
    }
  }
}

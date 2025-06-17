import { defineStore } from 'pinia'
import axios from 'axios'
// import Cookies from 'js-cookie' // Temporairement commenté

interface User {
  id: number
  username: string
  email: string
  token: string
}

// Durée de vie du cookie en jours (7 jours)
const COOKIE_EXPIRATION = 7

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    isAuthenticated: false,
    isLoading: false,
    error: null as string | null,
  }),

  actions: {
    setUser(userData: User) {
      console.log('Setting user:', userData);
      this.user = userData
      this.isAuthenticated = true
      
      // Utiliser localStorage au lieu de cookies temporairement
      localStorage.setItem('auth_user', JSON.stringify(userData))
      
      // Stocker les données utilisateur dans un cookie sécurisé
      /* Temporairement commenté
      Cookies.set('auth_user', JSON.stringify(userData), { 
        expires: COOKIE_EXPIRATION,
        secure: window.location.protocol === 'https:',
        sameSite: 'strict'
      })
      */
    },

    logout() {
      console.log('Logging out user');
      this.user = null
      this.isAuthenticated = false
      
      // Supprimer l'authentification du localStorage
      localStorage.removeItem('auth_user')
      
      // Supprimer le cookie d'authentification
      // Cookies.remove('auth_user') // Temporairement commenté
    },

    async validateToken() {
      try {
        this.isLoading = true
        this.error = null

        // Récupérer le token du localStorage
        const userData = localStorage.getItem('auth_user')
        if (!userData) {
          console.log('No stored user data found in localStorage');
          return false
        }

        const user = JSON.parse(userData)
        if (!user || !user.token) {
          console.log('Invalid stored user data or missing token');
          this.logout()
          return false
        }
        
        console.log('Validating token for user:', user.username);

        // Valider le token avec l'API FastAPI
        const response = await axios.post(
          `${import.meta.env.VITE_API_URL}/api/users/validate-token`,
          {},
          {
            headers: {
              Authorization: `Bearer ${user.token}`,
            },
          }
        )

        console.log('Token validation response:', response.data);

        if (response.data.valid) {
          // Mettre à jour les données utilisateur si nécessaire
          this.setUser({
            ...user,
            username: response.data.username,
            email: response.data.email,
          })
          return true
        } else {
          this.logout()
          return false
        }
      } catch (error) {
        console.error('Error validating token:', error)
        this.error = 'Erreur lors de la validation du token'
        this.logout()
        return false
      } finally {
        this.isLoading = false
      }
    },

    openAuthWindow() {
      const authUrl = `${import.meta.env.VITE_AUTH_URL}/index.php`
      console.log('Opening auth window with URL:', authUrl);
      
      // Fermer une éventuelle fenêtre déjà ouverte
      if (window.authWindow && !window.authWindow.closed) {
        window.authWindow.close();
      }
      
      // Ouvrir une nouvelle fenêtre
      const authWindow = window.open(authUrl, 'AuthMusicTogether', 'width=600,height=700')
      
      // Stocker la référence dans window pour pouvoir la fermer plus tard
      window.authWindow = authWindow;
      
      if (!authWindow) {
        console.error('Failed to open authentication window');
        this.error = 'Impossible d\'ouvrir la fenêtre d\'authentification. Veuillez désactiver votre bloqueur de pop-ups.'
        return
      }
      
      // Configurer le gestionnaire de messages globalement pour s'assurer qu'il fonctionne correctement
      const setupMessageListener = () => {
        console.log('Setting up message listener');
        
        // Supprimer l'ancien écouteur s'il existe déjà
        window.removeEventListener('message', this.handleAuthMessage);
        
        // Ajouter le nouvel écouteur
        window.addEventListener('message', this.handleAuthMessage);
      };
      
      // Appliquer immédiatement et réessayer après un court délai pour s'assurer qu'il est actif
      setupMessageListener();
      setTimeout(setupMessageListener, 500);
      
      // Vérifier périodiquement si la fenêtre a été fermée manuellement
      const checkClosed = setInterval(() => {
        if (authWindow && authWindow.closed) {
          clearInterval(checkClosed);
        }
      }, 1000);
    },
    
    // Gestionnaire d'événements de message externalisé pour cohérence
    handleAuthMessage(event: MessageEvent) {
      console.log('Message received:', event.data);
      
      if (event.data && event.data.type === 'auth_success') {
        // On utilise le store via sa référence globale ici car "this" n'est pas le store dans ce contexte
        const store = useAuthStore();
        console.log('Auth success message received:', event.data.data);
        
        // Mettre à jour l'état utilisateur
        store.setUser(event.data.data);
      }
    }
  },
})

// Augmenter l'interface Window pour permettre le stockage de la fenêtre d'authentification
declare global {
  interface Window {
    authWindow: WindowProxy | null;
  }
} 
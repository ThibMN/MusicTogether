import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Home from '../views/Home.vue'
import Room from '../views/Room.vue'

// Définir les routes
const routes: RouteRecordRaw[] = [
  { 
    path: '/', 
    component: Home,
    meta: { requiresAuth: false }
  },
  { 
    path: '/room/:roomCode', 
    component: Room,
    meta: { requiresAuth: false } // Temporairement désactivé pour debug
  }
]

// Créer le router
const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard pour vérifier l'authentification
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth

  console.log('Route navigation:', {
    to: to.fullPath,
    requiresAuth,
    isAuthenticated: authStore.isAuthenticated,
    user: authStore.user?.username
  });

  // Si la route nécessite une authentification
  if (requiresAuth) {
    // Vérifier si l'utilisateur est déjà authentifié
    if (!authStore.isAuthenticated) {
      // Si pas encore authentifié, essayer de valider le token
      const isValid = await authStore.validateToken()
      console.log('Token validation result:', isValid);
      
      if (!isValid) {
        console.log('Authentication required for route:', to.path)
        // Stocker la route cible pour redirection après connexion
        localStorage.setItem('redirect_after_login', to.fullPath)
        
        // Rediriger vers la page d'accueil
        next('/')
        return
      }
    }
  }
  
  // Si l'utilisateur est authentifié ou la route ne nécessite pas d'authentification
  next()
})

export default router 
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Import des routes
import Home from './views/Home.vue'
import Room from './views/Room.vue'

// Configuration des routes
const routes = [
  { path: '/', component: Home },
  { path: '/room/:roomCode', component: Room },
]

// Création du router
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Création de l'application
const app = createApp(App)

// Utilisation de Pinia et Vue Router
app.use(createPinia())
app.use(router)

// Montage de l'application
app.mount('#app')

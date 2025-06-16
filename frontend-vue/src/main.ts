import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import App from './App.vue'
import './style.css'

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

// Afficher les erreurs de montage
app.config.errorHandler = (err, instance, info) => {
  console.error('Vue Error:', err)
  console.error('Error Info:', info)
}

// Montage de l'application
app.mount('#app')

// Debug
console.log('Main.ts executed')

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://fastapi:8000',
        changeOrigin: true
      },
      '/auth': {
        target: 'http://php:8080',
        changeOrigin: true
      },
    },
  },
  define: {
    // Utiliser des valeurs statiques pour éviter les problèmes avec process.env
    '__VUE_OPTIONS_API__': true,
    '__VUE_PROD_DEVTOOLS__': false,
    'import.meta.env.VITE_API_URL': JSON.stringify('http://localhost:8000'),
    'import.meta.env.VITE_AUTH_URL': JSON.stringify('http://localhost:8080')
  }
})

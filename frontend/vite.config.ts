import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy API requests to Flask backend
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true,
        secure: false
      }
      // WebSocket connects directly to Flask (not through proxy)
    }
  }
})

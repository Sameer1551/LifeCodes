import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // Frontend runs on 3000
    proxy: {
      // Proxy API requests to the backend
      '/api': {
        target: 'http://127.0.0.1:8000', // Point this to your FastAPI/Flask server
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '') // Remove /api prefix if backend doesn't use it
      }
    }
  }
})

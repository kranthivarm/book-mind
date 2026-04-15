import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
    server: {
    port: 3000,
    // Proxy API calls to backend during development
    // This means /api/... in React → http://localhost:8000/api/...
    // You can remove this and use full URL in api.js if you prefer
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})

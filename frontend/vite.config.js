import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const API = process.env.VITE_API || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': API,
      '/ws': { target: API.replace('http', 'ws'), ws: true },
    },
  },
})

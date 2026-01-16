import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Backend API URL - override with VITE_API_URL env var
const apiUrl = process.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../sandboxy/ui/dist',
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    proxy: {
      '/api': apiUrl,
      '/ws': {
        target: apiUrl,
        ws: true,
      },
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Port ini harus cocok dengan CORS_ORIGINS di .env backend.
    port: 5173,
    strictPort: true,
  },
})

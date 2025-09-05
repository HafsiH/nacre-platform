import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/files': 'http://127.0.0.1:8123',
      '/conversions': 'http://127.0.0.1:8123',
      '/exports': 'http://127.0.0.1:8123',
      '/health': 'http://127.0.0.1:8123',
      '/sophie': 'http://127.0.0.1:8123',
    },
  },
})

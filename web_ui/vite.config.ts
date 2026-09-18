import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    allowedHosts: [
      'uninstall-enjoyable-splendid.ngrok-free.dev',
    ],
    proxy: { '/api': 'http://127.0.0.1:5000' },
  },
  build: { outDir: 'dist' },
})

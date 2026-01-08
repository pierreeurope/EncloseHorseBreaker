import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  // No React plugin needed - we're using their play.js directly
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
      },
    },
  },
})

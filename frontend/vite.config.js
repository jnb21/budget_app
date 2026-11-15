import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // The page calls /health and /api/... on its own address (localhost:5173);
    // Vite forwards those requests to the backend. The browser only ever talks
    // to one site, so the backend needs no CORS rules.
    proxy: {
      '/health': BACKEND,
      '/api': BACKEND,
    },
  },
  test: {
    // Tests run in Node; jsdom gives them a pretend browser page (document, window).
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'], // cleanup after each test
  },
})

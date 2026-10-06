import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The console talks straight to the two FastAPI services from the browser.
// Both services already allow cross-origin calls (CORS is open), so no proxy is needed.
export default defineConfig({
  plugins: [react()],
  server: { port: 5174 },
})

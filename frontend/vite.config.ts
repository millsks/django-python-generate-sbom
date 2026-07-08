import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// Config is command-aware (Story 20.8):
//   - `vite build` (production) → base '/static/' so the built asset URLs resolve
//     under Django's WhiteNoise static serving, and outDir stays `dist`
//     (frontend/dist/), which Django's STATICFILES_DIRS references (AD-5).
//   - `vite` (dev server, `pixi run fe-dev`) → base '/' and a proxy that forwards
//     API/admin/static calls to Django on :8000, so the SPA's relative `/api/...`
//     client (src/api/client.ts) works with HMR at http://localhost:5173 without a
//     separate build. The prod build is unaffected — its asset URLs stay '/static/'.
// Test config lives in vitest.config.ts.
const DJANGO_ORIGIN = 'http://localhost:8000'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/' : '/',
  plugins: [react()],
  server: {
    proxy: {
      // The SPA API client uses relative `/api/...` paths; forward them (and the
      // DRF browsable/Swagger + admin routes) to Django so dev-server requests hit
      // the real backend on :8000.
      '/api': { target: DJANGO_ORIGIN, changeOrigin: true },
      '/admin': { target: DJANGO_ORIGIN, changeOrigin: true },
      '/static': { target: DJANGO_ORIGIN, changeOrigin: true },
    },
  },
}))

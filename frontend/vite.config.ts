import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// base '/static/' so built asset URLs resolve under Django's WhiteNoise static
// serving; outDir defaults to `dist` (i.e. frontend/dist/), which Django's
// STATICFILES_DIRS references (AD-5).
export default defineConfig({
  base: '/static/',
  plugins: [react()],
})

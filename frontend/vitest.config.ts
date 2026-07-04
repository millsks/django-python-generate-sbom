import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Vitest config (kept separate from vite.config.ts so the production `tsc -b`
// build doesn't type-check the vitest-specific `test` block, which clashes with
// the rolldown-vite plugin types). Not referenced by any tsconfig.
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: false,
  },
})

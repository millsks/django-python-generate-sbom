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
    // v8 coverage with an lcov report (frontend/coverage/lcov.info) for the
    // Codecov `frontend` flag (Story 9.1). `text` keeps a terminal summary.
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/**/*.d.ts', 'src/main.tsx'],
      // Fail the coverage run (and thus `pixi run ci`, which now runs `fe-cov`) if
      // coverage regresses — a local guard so a frontend gap is caught before the PR
      // instead of only by Codecov's `frontend` flag. Set just under current totals;
      // raise these as coverage improves.
      thresholds: {
        statements: 84,
        branches: 85,
        functions: 65,
        lines: 84,
      },
    },
  },
})

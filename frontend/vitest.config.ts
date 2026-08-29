/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Separate from vite.config.ts so `vite build`/`vite dev` never pick up test
// globals or the coverage provider. Vitest merges this over vite.config.ts's
// shared options (plugins, resolve, etc.) automatically when both exist.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    css: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: ['node_modules/', 'src/__tests__/', '**/*.d.ts', 'src/main.tsx'],
    },
  },
});

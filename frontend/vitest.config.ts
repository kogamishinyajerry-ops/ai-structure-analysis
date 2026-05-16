// FM-04a Phase 7 E — headless frontend smoke harness configuration.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// vitest + jsdom + @testing-library/react for the Phase 6 E components
// (TrustScoreGauge / DriftNarrativePanel / TrustScoreTimelineChart).
// Closes Phase 6 carry-forward §2.

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./test/setup.ts'],
    // Phase 7 E — only the new component .test.tsx files. The legacy
    // .test.ts files use `node --test` (see frontend/test/*.test.ts);
    // we do not migrate them here. A future slice could either run them
    // under vitest too or keep two runners.
    include: ['test/**/*.test.tsx'],
    css: false,
  },
})

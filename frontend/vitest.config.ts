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
    // FM-04a — run BOTH the component `.test.tsx` files AND the logic
    // `.test.ts` files under one vitest runner. The legacy `.test.ts`
    // files were authored against `node:test`/`node:assert` but were
    // gated by no runner in CI; their `describe`/`it`/`test` imports
    // were migrated to vitest (node:assert kept — it is a Node builtin
    // that works under vitest, so assertion semantics are unchanged).
    include: ['test/**/*.test.{ts,tsx}'],
    css: false,
  },
})

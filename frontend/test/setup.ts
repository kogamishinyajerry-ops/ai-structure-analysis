// FM-04a Phase 7 E — vitest setup file.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Imports @testing-library/jest-dom so matchers like toBeInTheDocument()
// and toHaveTextContent() are available in every test file. Stubs
// global.fetch with a vitest spy so component-mount tests never hit
// the real network. Individual tests override the spy as needed.

import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

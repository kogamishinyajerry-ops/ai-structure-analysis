// FM-04a Phase 39 A — connectionLostRecoveryOptions test (Dim 2 novice).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Pins the recovery-option template for a dropped live-job log WebSocket —
// the 6th and last silent error-recovery path (Phase 33 C novice_simulator
// #2 + Phase 36 D friction (a), re-confirmed by the Phase 38 D R6 fleet as a
// HIGH novice friction). App.tsx `connectToLogs` ws.onerror now surfaces this
// payload via `setUploadError` (live-job context) instead of going silent
// after a single `[ERROR] WebSocket connection died` console line. The Retry
// (wired at the call-site) reconnects to the same job's log stream.

import { describe, expect, it } from 'vitest'
import { connectionLostRecoveryOptions } from '../src/state/useUploadErrorRecovery'

describe('Phase 39 A — connectionLostRecoveryOptions', () => {
  it('returns a titled, novice-readable recovery payload', () => {
    const opts = connectionLostRecoveryOptions('job-abc-123')
    expect(opts.title).toMatch(/connection lost/i)
    expect(opts.message).toContain('job-abc-123')
    expect(opts.message).toMatch(/solver may still be running/i)
  })

  it('embeds the jobId in the support code + a friendly pill label', () => {
    const opts = connectionLostRecoveryOptions('job-abc-123')
    expect(opts.code).toBe('WS-DISCONNECT:job-abc-123')
    expect(opts.codeFriendly).toBe('Connection lost')
  })

  it('lists actionable remediation steps (reconnect + reopen + check backend)', () => {
    const opts = connectionLostRecoveryOptions('job-abc-123')
    expect(opts.remediation).toBeTruthy()
    const steps = (opts.remediation ?? []).join(' ').toLowerCase()
    expect(steps).toMatch(/reconnect/)
    expect(steps).toMatch(/reopen the case/)
    expect(steps).toMatch(/backend|runner/)
  })

  it('does not falsely claim the job was stopped (a dropped stream != a stopped solver)', () => {
    const opts = connectionLostRecoveryOptions('job-abc-123')
    const all = `${opts.title} ${opts.message} ${(opts.remediation ?? []).join(' ')}`.toLowerCase()
    expect(all).toMatch(/may still be running|does not stop the job/)
  })
})

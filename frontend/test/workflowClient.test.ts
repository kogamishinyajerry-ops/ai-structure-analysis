// ADR-028 P1.5 — provenance surface unit tests: the parser must extract the
// machine-checkable provenance class, the coverage qualifier must count each
// class distinctly (deterministic + LLM never blurred), and triggerWorkflow must
// thread a genuine userRequest to the backend (so the wired intake agent runs).

import { describe, it, expect, vi } from 'vitest'
import {
  PROVENANCE_LABEL,
  parseStageState,
  parseWorkflowRun,
  provenanceCoverage,
  triggerWorkflow,
} from '../src/workflowClient.ts'

describe('workflowClient — ADR-028 provenance surface', () => {
  it('parseStageState extracts a known provenance class', () => {
    const st = parseStageState({ stage: 'project_intake', status: 'success', provenance: 'deterministic_agent' })
    expect(st.provenance).toBe('deterministic_agent')
  })

  it('defaults missing or unknown provenance to scripted_demo (never a false agent-driven)', () => {
    expect(parseStageState({ stage: 'x', status: 'success' }).provenance).toBe('scripted_demo')
    expect(parseStageState({ stage: 'x', status: 'success', provenance: 'human' }).provenance).toBe('scripted_demo')
  })

  it('provenanceCoverage counts each class distinctly (deterministic + LLM never blurred)', () => {
    const run = parseWorkflowRun({
      runId: 'r',
      stages: [
        { stage: 'a', status: 'success', provenance: 'deterministic_agent' },
        { stage: 'b', status: 'success', provenance: 'llm_agent' },
        { stage: 'c', status: 'success' },
        { stage: 'd', status: 'pending', provenance: 'scripted_demo' },
      ],
    })
    expect(run).not.toBeNull()
    if (run === null) return
    expect(provenanceCoverage(run.stages)).toEqual({
      deterministic: 1,
      llm: 1,
      scripted: 2,
      total: 4,
      agentDriven: 2,
    })
  })

  it('labels match the enum values verbatim', () => {
    expect(PROVENANCE_LABEL.scripted_demo).toBe('scripted demo')
    expect(PROVENANCE_LABEL.deterministic_agent).toBe('deterministic agent')
    expect(PROVENANCE_LABEL.llm_agent).toBe('LLM agent')
  })

  it('triggerWorkflow threads a genuine userRequest as camelCase', async () => {
    const bodies: Record<string, unknown>[] = []
    global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toContain('/workflow/trigger')
      bodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>)
      return { ok: true, status: 200, json: async () => ({ runId: 'r', stages: [] }) } as Response
    }) as unknown as typeof fetch
    await triggerWorkflow('/api/v1', { userRequest: '支架模态分析' })
    expect(bodies[0]?.userRequest).toBe('支架模态分析')
    expect(bodies[0]?.label).toBe('monitor')
  })

  it('sends null userRequest when none is given (intake stays scripted_demo)', async () => {
    const bodies: Record<string, unknown>[] = []
    global.fetch = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      bodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>)
      return { ok: true, status: 200, json: async () => ({ runId: 'r', stages: [] }) } as Response
    }) as unknown as typeof fetch
    await triggerWorkflow('/api/v1', {})
    expect(bodies[0]?.userRequest).toBeNull()
  })
})

describe('workflowClient — ADR-028 P-fidelity discriminator (never inflates N/13)', () => {
  it('keeps the flat fidelityTier disclosure but drops the nested fidelity evidence', () => {
    const st = parseStageState({
      stage: 'geometry_validation',
      status: 'success',
      provenance: 'deterministic_agent',
      metrics: {
        fidelityTier: 'tier_0_dummy',
        fidelity: { tier: 'tier_0_dummy', toolRan: true, dataReal: false, disclosure: 'x' },
        someNumber: 3,
      },
    })
    // flat string disclosure survives the parser -> auto-renders in the Monitor
    expect(st.metrics.fidelityTier).toBe('tier_0_dummy')
    // nested evidence object is dropped -> structurally cannot reach provenanceCoverage
    expect(st.metrics.fidelity).toBeUndefined()
  })

  it('a SCRIPTED stage carrying a tier_0_dummy fidelity flag is still NOT agent-driven', () => {
    const st = parseStageState({
      stage: 'x',
      status: 'success',
      provenance: 'scripted_demo',
      metrics: {
        fidelityTier: 'tier_0_dummy',
        fidelity: { tier: 'tier_0_dummy', toolRan: true, dataReal: false },
      },
    })
    // the count is keyed PURELY on provenance — a fidelity flag never inflates agentDriven
    expect(provenanceCoverage([st]).agentDriven).toBe(0)
  })
})

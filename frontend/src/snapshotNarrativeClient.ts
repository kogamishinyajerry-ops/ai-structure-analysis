// FM-04a Phase 6 C — Snapshot drift narrative client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/snapshot-narrative?a=<utc>&b=<utc>`.
// Preserves schemaVersion + every template_id verbatim (so the UI can
// route a known template to a custom icon without re-parsing).

export type Severity = 'info' | 'warn' | 'danger'

export interface NarrativeLine {
  templateId: string
  severity: Severity
  text: string
}

export interface CaseNarrative {
  caseId: string
  lines: NarrativeLine[]
}

// Phase 7 B — exposed locale set (kept here to avoid a network probe for
// the supported set). The default and supported list must stay aligned
// with backend/app/services/reporting/snapshot_narrative_catalogs.py.
export const SUPPORTED_NARRATIVE_LOCALES = ['en-US', 'zh-CN'] as const
export type NarrativeLocale = (typeof SUPPORTED_NARRATIVE_LOCALES)[number]
export const DEFAULT_NARRATIVE_LOCALE: NarrativeLocale = 'en-US'

export interface SnapshotNarrative {
  schemaVersion: string
  snapshotALabel: string
  snapshotBLabel: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  locale: string
  narratives: CaseNarrative[]
  claimImpact: string
}

interface RawLine {
  template_id?: string
  severity?: string
  text?: string
}

interface RawCaseNarrative {
  case_id?: string
  lines?: RawLine[]
}

interface RawSnapshotNarrative {
  schema_version?: string
  snapshot_a_label?: string
  snapshot_b_label?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  locale?: string
  narratives?: RawCaseNarrative[]
  claim_impact?: string
}

function parseSeverity(raw: string | undefined): Severity {
  if (raw === 'warn' || raw === 'danger') return raw
  return 'info'
}

function parseLine(raw: RawLine | null | undefined): NarrativeLine | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.template_id !== 'string') return null
  return {
    templateId: raw.template_id,
    severity: parseSeverity(raw.severity),
    text: raw.text ?? '',
  }
}

function parseCaseNarrative(
  raw: RawCaseNarrative | null | undefined,
): CaseNarrative | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    caseId: raw.case_id,
    lines: (raw.lines ?? [])
      .map(parseLine)
      .filter((line): line is NarrativeLine => line !== null),
  }
}

export function parseSnapshotNarrative(
  raw: RawSnapshotNarrative | null | undefined,
): SnapshotNarrative | null {
  if (!raw || typeof raw !== 'object') return null
  if (
    typeof raw.snapshot_a_label !== 'string' ||
    typeof raw.snapshot_b_label !== 'string'
  ) {
    return null
  }
  return {
    schemaVersion: raw.schema_version ?? '',
    snapshotALabel: raw.snapshot_a_label,
    snapshotBLabel: raw.snapshot_b_label,
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    locale: raw.locale ?? DEFAULT_NARRATIVE_LOCALE,
    narratives: (raw.narratives ?? [])
      .map(parseCaseNarrative)
      .filter((n): n is CaseNarrative => n !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface SnapshotNarrativeFetchResult {
  narrative: SnapshotNarrative | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchSnapshotNarrative(
  apiBase: string,
  labelA: string,
  labelB: string,
  signal?: AbortSignal,
  locale: NarrativeLocale = DEFAULT_NARRATIVE_LOCALE,
): Promise<SnapshotNarrativeFetchResult> {
  const params = new URLSearchParams({ a: labelA, b: labelB, locale })
  const url = `${apiBase.replace(/\/$/, '')}/snapshot-narrative?${params.toString()}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`snapshot-narrative endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawSnapshotNarrative
    const parsed = parseSnapshotNarrative(raw)
    if (!parsed) {
      throw new Error('snapshot-narrative payload is malformed')
    }
    return { narrative: parsed, source: 'live' }
  } catch (err) {
    return {
      narrative: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

// helper: group lines by severity for tone-coded UI rendering
export function groupBySeverity(
  lines: NarrativeLine[],
): { info: NarrativeLine[]; warn: NarrativeLine[]; danger: NarrativeLine[] } {
  const out = {
    info: [] as NarrativeLine[],
    warn: [] as NarrativeLine[],
    danger: [] as NarrativeLine[],
  }
  for (const line of lines) {
    out[line.severity].push(line)
  }
  return out
}

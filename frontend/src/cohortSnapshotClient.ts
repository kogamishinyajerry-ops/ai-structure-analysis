// FM-04a Phase 5 C/D — Cohort snapshot listing + diff clients.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Two endpoints in one client module:
// - GET /api/v1/cohort-snapshots         — listing of past snapshots
// - GET /api/v1/cohort-snapshot-diff     — diff between two snapshots
//
// Both surfaces preserve schemaVersion per the Phase 5 X-axis
// anti-gaming guard (-2 if any frontend client silently drops it).

// ---------- listing ----------

export interface SnapshotListingEntry {
  schemaVersion: string
  snapshotLabel: string
  capturedAtUtc: string | null
  claimTier: string
  claimBoundary: string
  cohortCount: number
  cases: string[]
  reviewerBundleWritten: boolean
}

export interface SnapshotListing {
  schemaVersion: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  snapshotCount: number
  snapshots: SnapshotListingEntry[]
  claimImpact: string
}

interface RawSnapshotListingEntry {
  schema_version?: string
  snapshot_label?: string
  captured_at_utc?: string | null
  claim_tier?: string
  claim_boundary?: string
  cohort_count?: number
  cases?: string[]
  reviewer_bundle_written?: boolean
}

interface RawSnapshotListing {
  schema_version?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  snapshot_count?: number
  snapshots?: RawSnapshotListingEntry[]
  claim_impact?: string
}

function parseSnapshotEntry(
  raw: RawSnapshotListingEntry | null | undefined,
): SnapshotListingEntry | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.snapshot_label !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    snapshotLabel: raw.snapshot_label,
    capturedAtUtc: raw.captured_at_utc ?? null,
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    cohortCount: raw.cohort_count ?? 0,
    cases: raw.cases ?? [],
    reviewerBundleWritten: raw.reviewer_bundle_written ?? false,
  }
}

export function parseSnapshotListing(
  raw: RawSnapshotListing | null | undefined,
): SnapshotListing | null {
  if (!raw || typeof raw !== 'object') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    snapshotCount: raw.snapshot_count ?? 0,
    snapshots: (raw.snapshots ?? [])
      .map(parseSnapshotEntry)
      .filter((e): e is SnapshotListingEntry => e !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface SnapshotListingFetchResult {
  listing: SnapshotListing | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchSnapshotListing(
  apiBase: string,
  signal?: AbortSignal,
): Promise<SnapshotListingFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/cohort-snapshots`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`cohort-snapshots endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawSnapshotListing
    const parsed = parseSnapshotListing(raw)
    if (!parsed) {
      throw new Error('cohort-snapshots payload is malformed')
    }
    return { listing: parsed, source: 'live' }
  } catch (err) {
    return {
      listing: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

// ---------- diff ----------

export interface CompletenessDelta {
  caseId: string
  aScore: number | null
  bScore: number | null
  delta: number | null
}

export interface PackageVersionChange {
  name: string
  aVersion: string | null
  bVersion: string | null
}

export interface ScriptShaChange {
  relpath: string
  aSha256: string | null
  bSha256: string | null
}

export interface ReproducibilityDelta {
  caseId: string
  aGitSha: string | null
  bGitSha: string | null
  gitShaChanged: boolean
  aGitDirty: boolean | null
  bGitDirty: boolean | null
  dirtyChanged: boolean
  aPythonVersion: string | null
  bPythonVersion: string | null
  pythonVersionChanged: boolean
  packageVersionChanges: PackageVersionChange[]
  scriptShaChanges: ScriptShaChange[]
}

export interface CohortSnapshotDiff {
  schemaVersion: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  snapshotALabel: string
  snapshotBLabel: string
  aCohortCount: number
  bCohortCount: number
  cohortAdded: string[]
  cohortRemoved: string[]
  cohortShared: string[]
  completenessDeltas: CompletenessDelta[]
  reproducibilityDeltas: ReproducibilityDelta[]
  claimImpact: string
}

interface RawCompletenessDelta {
  case_id?: string
  a_score?: number | null
  b_score?: number | null
  delta?: number | null
}

interface RawPackageChange {
  name?: string
  a_version?: string | null
  b_version?: string | null
}

interface RawScriptChange {
  relpath?: string
  a_sha256?: string | null
  b_sha256?: string | null
}

interface RawReproducibilityDelta {
  case_id?: string
  a_git_sha?: string | null
  b_git_sha?: string | null
  git_sha_changed?: boolean
  a_git_dirty?: boolean | null
  b_git_dirty?: boolean | null
  dirty_changed?: boolean
  a_python_version?: string | null
  b_python_version?: string | null
  python_version_changed?: boolean
  package_version_changes?: RawPackageChange[]
  script_sha_changes?: RawScriptChange[]
}

interface RawCohortSnapshotDiff {
  schema_version?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  snapshot_a_label?: string
  snapshot_b_label?: string
  a_cohort_count?: number
  b_cohort_count?: number
  cohort_added?: string[]
  cohort_removed?: string[]
  cohort_shared?: string[]
  completeness_deltas?: RawCompletenessDelta[]
  reproducibility_deltas?: RawReproducibilityDelta[]
  claim_impact?: string
}

function parseCompletenessDelta(
  raw: RawCompletenessDelta | null | undefined,
): CompletenessDelta | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    caseId: raw.case_id,
    aScore: raw.a_score ?? null,
    bScore: raw.b_score ?? null,
    delta: raw.delta ?? null,
  }
}

function parsePackageChange(
  raw: RawPackageChange | null | undefined,
): PackageVersionChange | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.name !== 'string') return null
  return {
    name: raw.name,
    aVersion: raw.a_version ?? null,
    bVersion: raw.b_version ?? null,
  }
}

function parseScriptChange(
  raw: RawScriptChange | null | undefined,
): ScriptShaChange | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.relpath !== 'string') return null
  return {
    relpath: raw.relpath,
    aSha256: raw.a_sha256 ?? null,
    bSha256: raw.b_sha256 ?? null,
  }
}

function parseReproDelta(
  raw: RawReproducibilityDelta | null | undefined,
): ReproducibilityDelta | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    caseId: raw.case_id,
    aGitSha: raw.a_git_sha ?? null,
    bGitSha: raw.b_git_sha ?? null,
    gitShaChanged: raw.git_sha_changed ?? false,
    aGitDirty: raw.a_git_dirty ?? null,
    bGitDirty: raw.b_git_dirty ?? null,
    dirtyChanged: raw.dirty_changed ?? false,
    aPythonVersion: raw.a_python_version ?? null,
    bPythonVersion: raw.b_python_version ?? null,
    pythonVersionChanged: raw.python_version_changed ?? false,
    packageVersionChanges: (raw.package_version_changes ?? [])
      .map(parsePackageChange)
      .filter((c): c is PackageVersionChange => c !== null),
    scriptShaChanges: (raw.script_sha_changes ?? [])
      .map(parseScriptChange)
      .filter((c): c is ScriptShaChange => c !== null),
  }
}

export function parseCohortSnapshotDiff(
  raw: RawCohortSnapshotDiff | null | undefined,
): CohortSnapshotDiff | null {
  if (!raw || typeof raw !== 'object') return null
  if (
    typeof raw.snapshot_a_label !== 'string' ||
    typeof raw.snapshot_b_label !== 'string'
  ) {
    return null
  }
  return {
    schemaVersion: raw.schema_version ?? '',
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    snapshotALabel: raw.snapshot_a_label,
    snapshotBLabel: raw.snapshot_b_label,
    aCohortCount: raw.a_cohort_count ?? 0,
    bCohortCount: raw.b_cohort_count ?? 0,
    cohortAdded: raw.cohort_added ?? [],
    cohortRemoved: raw.cohort_removed ?? [],
    cohortShared: raw.cohort_shared ?? [],
    completenessDeltas: (raw.completeness_deltas ?? [])
      .map(parseCompletenessDelta)
      .filter((d): d is CompletenessDelta => d !== null),
    reproducibilityDeltas: (raw.reproducibility_deltas ?? [])
      .map(parseReproDelta)
      .filter((d): d is ReproducibilityDelta => d !== null),
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface CohortSnapshotDiffFetchResult {
  diff: CohortSnapshotDiff | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchCohortSnapshotDiff(
  apiBase: string,
  labelA: string,
  labelB: string,
  signal?: AbortSignal,
): Promise<CohortSnapshotDiffFetchResult> {
  const params = new URLSearchParams({ a: labelA, b: labelB })
  const url = `${apiBase.replace(/\/$/, '')}/cohort-snapshot-diff?${params.toString()}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`cohort-snapshot-diff endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawCohortSnapshotDiff
    const parsed = parseCohortSnapshotDiff(raw)
    if (!parsed) {
      throw new Error('cohort-snapshot-diff payload is malformed')
    }
    return { diff: parsed, source: 'live' }
  } catch (err) {
    return {
      diff: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

// ---------- helpers shared by snapshot picker / drift panel ----------

export function snapshotLabelIsValid(label: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{6}Z$/.test(label)
}

export function summarizeCompletenessDrift(
  diff: CohortSnapshotDiff,
): { improved: number; regressed: number; unchanged: number } {
  let improved = 0
  let regressed = 0
  let unchanged = 0
  for (const d of diff.completenessDeltas) {
    if (d.delta === null) continue
    if (d.delta > 0) improved += 1
    else if (d.delta < 0) regressed += 1
    else unchanged += 1
  }
  return { improved, regressed, unchanged }
}

export function summarizeReproDrift(
  diff: CohortSnapshotDiff,
): { gitChanged: number; pythonChanged: number; scriptsChanged: number } {
  let gitChanged = 0
  let pythonChanged = 0
  let scriptsChanged = 0
  for (const d of diff.reproducibilityDeltas) {
    if (d.gitShaChanged) gitChanged += 1
    if (d.pythonVersionChanged) pythonChanged += 1
    if (d.scriptShaChanges.length > 0) scriptsChanged += 1
  }
  return { gitChanged, pythonChanged, scriptsChanged }
}

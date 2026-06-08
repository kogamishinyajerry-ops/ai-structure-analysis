// FM-04a Phase 5 B — Reproducibility manifest client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed fetch helper for `/api/v1/reproducibility-manifest/<case-id>`.
// Surfaces git state, Python env, tracked package versions, and
// generator script SHA-256 fingerprints. The schemaVersion field is
// preserved on the parsed object per the Phase 5 X-axis anti-gaming
// guard (-2 if any frontend client silently drops schemaVersion).

export interface ScriptFingerprint {
  relpath: string
  sha256: string
  bytes: number
}

export interface PackageFingerprint {
  name: string
  version: string
}

export interface ReproducibilityManifest {
  schemaVersion: string
  caseId: string
  generatedAtUtc: string
  claimTier: string
  claimBoundary: string
  gitCommitSha: string | null
  gitBranch: string | null
  gitDirty: boolean
  pythonVersion: string
  pythonImplementation: string
  platformSummary: string
  trackedPackages: PackageFingerprint[]
  scripts: ScriptFingerprint[]
  tier2BlockersRemaining: string[]
  claimImpact: string
}

interface RawScript {
  relpath?: string
  sha256?: string
  bytes?: number
}

interface RawPackage {
  name?: string
  version?: string
}

interface RawManifest {
  schema_version?: string
  case_id?: string
  generated_at_utc?: string
  claim_tier?: string
  claim_boundary?: string
  git_commit_sha?: string | null
  git_branch?: string | null
  git_dirty?: boolean
  python_version?: string
  python_implementation?: string
  platform_summary?: string
  tracked_packages?: RawPackage[]
  scripts?: RawScript[]
  tier2_blockers_remaining?: string[]
  claim_impact?: string
}

function parseScript(raw: RawScript | null | undefined): ScriptFingerprint | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.relpath !== 'string' || typeof raw.sha256 !== 'string') return null
  return {
    relpath: raw.relpath,
    sha256: raw.sha256,
    bytes: raw.bytes ?? 0,
  }
}

function parsePackage(raw: RawPackage | null | undefined): PackageFingerprint | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.name !== 'string') return null
  return {
    name: raw.name,
    version: raw.version ?? 'not_installed',
  }
}

export function parseReproducibilityManifest(
  raw: RawManifest | null | undefined,
): ReproducibilityManifest | null {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.case_id !== 'string') return null
  return {
    schemaVersion: raw.schema_version ?? '',
    caseId: raw.case_id,
    generatedAtUtc: raw.generated_at_utc ?? '',
    claimTier: raw.claim_tier ?? '',
    claimBoundary: raw.claim_boundary ?? '',
    gitCommitSha: raw.git_commit_sha ?? null,
    gitBranch: raw.git_branch ?? null,
    gitDirty: raw.git_dirty ?? false,
    pythonVersion: raw.python_version ?? '',
    pythonImplementation: raw.python_implementation ?? '',
    platformSummary: raw.platform_summary ?? '',
    trackedPackages: (raw.tracked_packages ?? [])
      .map(parsePackage)
      .filter((p): p is PackageFingerprint => p !== null),
    scripts: (raw.scripts ?? [])
      .map(parseScript)
      .filter((s): s is ScriptFingerprint => s !== null),
    tier2BlockersRemaining: raw.tier2_blockers_remaining ?? [],
    claimImpact: raw.claim_impact ?? '',
  }
}

export interface ReproducibilityManifestFetchResult {
  manifest: ReproducibilityManifest | null
  source: 'live' | 'fallback'
  error?: string
}

export async function fetchReproducibilityManifest(
  apiBase: string,
  caseId: string,
  signal?: AbortSignal,
): Promise<ReproducibilityManifestFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/reproducibility-manifest/${encodeURIComponent(caseId)}`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`reproducibility-manifest endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawManifest
    const parsed = parseReproducibilityManifest(raw)
    if (!parsed) {
      throw new Error('reproducibility-manifest payload is malformed')
    }
    return { manifest: parsed, source: 'live' }
  } catch (err) {
    return {
      manifest: null,
      source: 'fallback',
      error: err instanceof Error ? err.message : 'unknown error',
    }
  }
}

export function shortenCommit(sha: string | null): string {
  if (!sha) return 'unknown'
  return sha.length >= 7 ? sha.slice(0, 7) : sha
}

export function gitStateLabel(manifest: ReproducibilityManifest): string {
  if (!manifest.gitCommitSha) {
    return 'git state unavailable'
  }
  const short = shortenCommit(manifest.gitCommitSha)
  const branch = manifest.gitBranch ?? 'detached'
  const dirty = manifest.gitDirty ? ' (dirty)' : ''
  return `${branch}@${short}${dirty}`
}

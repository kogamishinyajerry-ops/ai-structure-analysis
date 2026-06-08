// FM-04a Phase 4 F — Reviewer bundle client.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// URL builder + multi-select toggle helper for the
// /api/v1/reviewer-bundle endpoint. The bundle is a Tier 1 reviewer
// hand-off, NOT a sealed FM-04b P8 packet; the rendered UI surface
// must preserve that wording.

export function reviewerBundleUrl(apiBase: string, caseIds: string[]): string {
  const trimmed = caseIds.map((id) => id.trim()).filter((id) => id.length > 0)
  if (trimmed.length === 0) {
    throw new Error('reviewerBundleUrl: at least one case id required')
  }
  const csv = trimmed.join(',')
  return `${apiBase.replace(/\/$/, '')}/reviewer-bundle?ids=${encodeURIComponent(csv)}`
}

export function toggleSelection(current: string[], caseId: string): string[] {
  const index = current.indexOf(caseId)
  if (index >= 0) {
    return current.filter((id) => id !== caseId)
  }
  return [...current, caseId]
}

export function reviewerBundleClaimImpact(caseCount: number): string {
  return (
    `Tier 1 candidate reviewer bundle (${caseCount} case${caseCount === 1 ? '' : 's'}) ` +
    'only; not signed validation; not benchmark agreement; not a sealed ' +
    'FM-04b P8 packet.'
  )
}

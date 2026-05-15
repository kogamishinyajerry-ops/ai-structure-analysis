// FM-04a Phase 4 F — Reviewer bundle client tests.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.

import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  reviewerBundleClaimImpact,
  reviewerBundleUrl,
  toggleSelection,
} from '../src/reviewerBundleClient.ts'

describe('reviewer bundle client', () => {
  it('builds the bundle URL with CSV ids', () => {
    const url = reviewerBundleUrl('http://example/api/v1', ['GS-A-candidate', 'GS-B-candidate'])
    assert.equal(
      url,
      'http://example/api/v1/reviewer-bundle?ids=GS-A-candidate%2CGS-B-candidate',
    )
  })

  it('strips empty and whitespace-only ids before building the URL', () => {
    const url = reviewerBundleUrl('http://example/api/v1', [
      'GS-A-candidate',
      ' ',
      'GS-B-candidate ',
    ])
    assert.equal(
      url,
      'http://example/api/v1/reviewer-bundle?ids=GS-A-candidate%2CGS-B-candidate',
    )
  })

  it('throws when no ids are supplied', () => {
    assert.throws(() => reviewerBundleUrl('http://example/api/v1', []), /at least one/)
    assert.throws(() => reviewerBundleUrl('http://example/api/v1', ['', '   ']), /at least one/)
  })

  it('handles trailing slash on the apiBase', () => {
    const url = reviewerBundleUrl('http://example/api/v1/', ['GS-A-candidate'])
    assert.equal(url, 'http://example/api/v1/reviewer-bundle?ids=GS-A-candidate')
  })

  it('toggleSelection adds and removes ids idempotently', () => {
    let state: string[] = []
    state = toggleSelection(state, 'GS-A-candidate')
    state = toggleSelection(state, 'GS-B-candidate')
    assert.deepEqual(state, ['GS-A-candidate', 'GS-B-candidate'])
    state = toggleSelection(state, 'GS-A-candidate')
    assert.deepEqual(state, ['GS-B-candidate'])
  })

  it('claim impact text preserves Tier 1 boundary wording', () => {
    const text = reviewerBundleClaimImpact(3).toLowerCase()
    assert.match(text, /not signed validation/)
    assert.match(text, /not benchmark agreement/)
    assert.match(text, /not a sealed fm-04b p8 packet/)
    // Forbidden positive-claim audit after stripping the disclaimers.
    const stripped = text
      .replace(/not signed validation/g, '')
      .replace(/not benchmark agreement/g, '')
    assert.equal(/validated against/.test(stripped), false)
    assert.equal(/perforation completed/.test(stripped), false)
  })

  it('claim impact pluralizes correctly', () => {
    assert.match(reviewerBundleClaimImpact(1), /\(1 case\)/)
    assert.match(reviewerBundleClaimImpact(5), /\(5 cases\)/)
  })
})

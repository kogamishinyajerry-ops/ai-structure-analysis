// FM-04a Phase 23 C — node-picking with field probe overlay tests.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Phase 23 C ships a click-to-pick reviewer-driven inspection
// feature: left-click without drag triggers a raycast, finds the
// closest node, and renders a HUD overlay with node label + xyz +
// field value. Escape clears the pick. `onNodePicked` callback
// forwards events to the parent.
//
// Anti-gaming guards:
//   * C:-1 — the click threshold is in screen-pixel space (4 px);
//     pinned via the helper's pure-function behavior + the
//     mousedown→mouseup distance gate.
//   * C:-2 — the picked node label MUST come from the frame's
//     `nodes` list, never a synthetic index. Pinned by the
//     findClosestNode test with shuffled node labels.

import { describe, expect, it } from 'vitest'
import {
  findClosestNode,
  fieldValueAtNode,
} from '../src/components/ResultMeshWebGLViewport'
import type { ResultMeshFrame } from '../src/resultMeshPlayback'

const shuffledFrame: ResultMeshFrame = {
  frame: 0,
  timeMs: 0,
  nodes: [
    // Note: labels are NOT consecutive — they're 7, 42, 99, 11.
    // Anti-gaming guard C:-2 requires findClosestNode to return
    // the actual label, not the array index.
    { label: 7, coordinates: [0, 0, 0] },
    { label: 42, coordinates: [1, 0, 0] },
    { label: 99, coordinates: [1, 1, 0] },
    { label: 11, coordinates: [0, 1, 0] },
  ],
  elements: [
    {
      label: 1,
      type: 'QUAD',
      connectivity: [7, 42, 99, 11],
      partRole: 'plate',
      alive: true,
      value: 100,
    },
  ],
}

const nodeCoordsFromFrame = (frame: ResultMeshFrame) => {
  const map = new Map<number, [number, number, number]>()
  for (const node of frame.nodes) {
    if (node.coordinates && node.coordinates.length >= 3) {
      map.set(node.label, [
        node.coordinates[0],
        node.coordinates[1],
        node.coordinates[2],
      ])
    }
  }
  return map
}

describe('findClosestNode — Phase 23 C C:-2 guard pin', () => {
  it('returns the correct label for a shuffled-label frame', () => {
    const nodeCoords = nodeCoordsFromFrame(shuffledFrame)
    const result = findClosestNode(shuffledFrame, [0.95, 0.05, 0], nodeCoords)
    expect(result).not.toBeNull()
    // Closest to (0.95, 0.05, 0) is node 42 at (1, 0, 0).
    expect(result?.label).toBe(42)
  })

  it('returns null on an empty frame', () => {
    const empty: ResultMeshFrame = {
      frame: 0,
      timeMs: 0,
      nodes: [],
      elements: [],
    }
    expect(findClosestNode(empty, [0, 0, 0], new Map())).toBeNull()
  })

  it('returns distance computed from world coords', () => {
    const nodeCoords = nodeCoordsFromFrame(shuffledFrame)
    const result = findClosestNode(shuffledFrame, [0, 0, 0], nodeCoords)
    expect(result?.label).toBe(7)
    expect(result?.distance).toBeCloseTo(0, 6)
  })

  it('uses world-space (post-magnification) coords, not undeformed', () => {
    // The function takes a `nodeCoords` map directly, so the caller
    // controls which coord set is used. This pins the contract:
    // findClosestNode reads from the map, not from frame.nodes[].coordinates.
    const customCoords = new Map<number, [number, number, number]>()
    customCoords.set(42, [10, 0, 0]) // moved
    customCoords.set(7, [0, 0, 0])
    const result = findClosestNode(shuffledFrame, [10, 0.1, 0], customCoords)
    expect(result?.label).toBe(42)
    expect(result?.position).toEqual([10, 0, 0])
  })
})

describe('fieldValueAtNode — Phase 23 C field probe', () => {
  it('returns the element value when the node is connected to an element with value', () => {
    expect(fieldValueAtNode(shuffledFrame, 42, 'mises')).toBe(100)
  })

  it('returns the tensor-derived value when stressTensor present', () => {
    const tensorFrame: ResultMeshFrame = {
      ...shuffledFrame,
      elements: [
        {
          ...shuffledFrame.elements[0],
          stressTensor: { sxx: 100, syy: 0, szz: 0, sxy: 0, syz: 0, sxz: 0 },
        },
      ],
    }
    expect(fieldValueAtNode(tensorFrame, 42, 'mises')).toBeCloseTo(100, 4)
    expect(fieldValueAtNode(tensorFrame, 42, 'sxx')).toBeCloseTo(100, 4)
    expect(fieldValueAtNode(tensorFrame, 42, 'syy')).toBeCloseTo(0, 4)
  })

  it('returns null for a node not connected to any element', () => {
    const orphanFrame: ResultMeshFrame = {
      ...shuffledFrame,
      nodes: [...shuffledFrame.nodes, { label: 555, coordinates: [99, 99, 99] }],
    }
    expect(fieldValueAtNode(orphanFrame, 555, 'mises')).toBeNull()
  })

  it('returns null when no elements have a value or tensor', () => {
    const valuelessFrame: ResultMeshFrame = {
      ...shuffledFrame,
      elements: [
        {
          label: 1,
          type: 'QUAD',
          connectivity: [7, 42, 99, 11],
          partRole: 'plate',
          alive: true,
          // No value, no stressTensor.
        },
      ],
    }
    expect(fieldValueAtNode(valuelessFrame, 42, 'mises')).toBeNull()
  })
})

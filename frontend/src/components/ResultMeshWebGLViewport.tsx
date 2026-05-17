import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import type { ResultMeshElement, ResultMeshFrame } from '../resultMeshPlayback';
import { componentValue, type StressComponent } from '../stressDerivatives';

// FM-04a Phase 21 C — minimal three.js WebGL viewport for the
// dynamic result-mesh playback. Reads the SAME `selectedFrame` shape
// that `ResultMeshPlaybackPanel`'s SVG body consumes (so the WebGL +
// SVG paths share the upstream data contract) and renders the
// elements as a THREE.Mesh with per-vertex stress coloring.
//
// Honest scope (Phase 21 C):
// * Single-frame static render. Frame changes rebuild the geometry
//   (no animation tweening between frames).
// * Color gradient matches the SVG legend (blue → green → orange).
// * Orbit (mouse drag) / pan (right-button drag) / zoom (wheel) via
//   a minimal hand-rolled camera controller. OrbitControls is in
//   three/examples but pulling that path adds bundle weight and
//   doesn't pay off for the Phase 21 C deliverable.
// * Volume elements (4-node tet / 8-node hex) are exploded into
//   their face triangles. 3-node faces render directly.
// * Falls back to a "WebGL unavailable" surface if context creation
//   fails (jsdom test env, browsers with WebGL disabled).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

export interface SectionCutState {
  /** Axis the clipping plane is perpendicular to. */
  axis: 'x' | 'y' | 'z';
  /** Position along the axis (m) at which the plane sits. */
  positionM: number;
  /** When true, render only the "low" half (coord < positionM).
   * When false, render only the "high" half. */
  showLow: boolean;
}

/** FM-04a Phase 23 D — element-value threshold filter.
 *
 * When set, elements whose derived field value falls outside
 * [minValue, maxValue] (inverted when `mode === 'outside'`) are
 * excluded from the BufferGeometry build. Elements without a value
 * are retained regardless of filter — see anti-gaming guard D:-1. */
export interface ValueFilterState {
  /** Lower bound; null means -∞. */
  minValue: number | null;
  /** Upper bound; null means +∞. */
  maxValue: number | null;
  /** 'inside' keeps elements inside [minValue, maxValue];
   *  'outside' keeps elements OUTSIDE that range. */
  mode: 'inside' | 'outside';
}

interface ResultMeshWebGLViewportProps {
  frame: ResultMeshFrame | null;
  valueMin: number;
  valueMax: number;
  /** FM-04a Phase 22 B — frame-to-frame animation. When defined +
   * playing=true, the viewport interpolates node positions between
   * `frame` and `nextFrame` at 60fps via requestAnimationFrame. When
   * undefined, falls back to Phase 21 C single-frame static render. */
  nextFrame?: ResultMeshFrame | null;
  playing?: boolean;
  /** FM-04a Phase 22 B — deformation magnification (1× default). */
  deformationScale?: number;
  /** FM-04a Phase 22 B — section-cut clipping plane. When defined,
   * one half of the mesh is hidden. */
  sectionCut?: SectionCutState | null;
  /** FM-04a Phase 23 B — stress-tensor component switcher. When the
   * frame elements carry `stressTensor`, this prop selects which
   * scalar derives the per-element color. Defaults to 'mises'.
   * Elements without a tensor fall back to the `value` field. */
  fieldComponent?: StressComponent;
  /** FM-04a Phase 23 C — node-pick callback. Fires when the reviewer
   * left-clicks the canvas (without dragging) and the raycaster
   * finds a node within hit tolerance. Forwards a `PickedNodeInfo`
   * to the parent so the panel can surface the probe in its info
   * pane. Passing `null` indicates "no pick" (Escape pressed or
   * click missed all geometry). */
  onNodePicked?: (info: PickedNodeInfo | null) => void;
  /** FM-04a Phase 23 D — element-value threshold filter. When set,
   * elements outside (inside, with mode='outside') the [minValue,
   * maxValue] range drop out of the rendered geometry. Elements
   * without a `value` are RETAINED regardless of filter (D:-1
   * anti-gaming guard — projectile parts etc. shouldn't silently
   * disappear). */
  valueFilter?: ValueFilterState | null;
}

/** FM-04a Phase 23 C — payload of a successful node pick. */
export interface PickedNodeInfo {
  /** Original node label from the frame's `nodes` list. */
  label: number;
  /** World-space coordinates (m). */
  position: [number, number, number];
  /** The scalar value the viewport is currently coloring by
   * (Mises / σ_xx / etc — depends on `fieldComponent`). Falls back
   * to `value` when no tensor is present. May be `null` when no
   * element near the picked node carries a value. */
  fieldValue: number | null;
}

// Tet (4-node) faces, 0-indexed into the connectivity array.
const TET_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 1, 2],
  [0, 1, 3],
  [1, 2, 3],
  [0, 2, 3],
];

// Hex (8-node) faces split into two triangles per face. Indices follow
// the CalculiX C3D8 convention: bottom 0-1-2-3, top 4-5-6-7 with 4 above
// 0, etc.
const HEX_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 1, 2], [0, 2, 3], // bottom
  [4, 6, 5], [4, 7, 6], // top
  [0, 5, 1], [0, 4, 5], // front
  [1, 6, 2], [1, 5, 6], // right
  [2, 7, 3], [2, 6, 7], // back
  [3, 4, 0], [3, 7, 4], // left
];

// Quad face (4-node) split into two triangles.
const QUAD_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 1, 2],
  [0, 2, 3],
];

interface Triangle {
  positions: [number, number, number, number, number, number, number, number, number];
  colorRgb: [number, number, number];
}

function elementTriangles(
  element: ResultMeshElement,
  nodeCoords: Map<number, [number, number, number]>,
  colorRgb: [number, number, number],
): Triangle[] {
  const connectivity = element.connectivity;
  if (!connectivity || connectivity.length < 3) return [];

  let faceTable: ReadonlyArray<readonly [number, number, number]>;
  if (connectivity.length === 4) {
    // 4-node element: either a quad (planar 4 nodes) or a tet (3D 4
    // nodes). Both render fine when treated as a tet; for a planar
    // quad, two of the four "tet faces" collapse, leaving the visible
    // surface. The honest, simple, conservative choice — Phase 21 C
    // doesn't need to disambiguate.
    faceTable = TET_FACES;
  } else if (connectivity.length === 8) {
    faceTable = HEX_FACES;
  } else if (connectivity.length === 3) {
    faceTable = [[0, 1, 2]];
  } else if (connectivity.length === 4) {
    faceTable = QUAD_FACES;
  } else {
    // Higher-order or unsupported element kinds: triangulate as a
    // simple fan from node 0. Far from accurate for curved elements
    // but keeps the viewport from going blank on unexpected input.
    faceTable = Array.from({ length: connectivity.length - 2 }, (_, i) => [
      0,
      i + 1,
      i + 2,
    ] as readonly [number, number, number]);
  }

  const out: Triangle[] = [];
  for (const [a, b, c] of faceTable) {
    const pa = nodeCoords.get(connectivity[a]);
    const pb = nodeCoords.get(connectivity[b]);
    const pc = nodeCoords.get(connectivity[c]);
    if (!pa || !pb || !pc) continue;
    out.push({
      positions: [...pa, ...pb, ...pc] as Triangle['positions'],
      colorRgb,
    });
  }
  return out;
}

function gradientStop(t: number): [number, number, number] {
  const tc = Math.max(0, Math.min(1, t));
  // blue (#2563eb = 37/99/235) → green (#10b981 = 16/185/129) → orange (#f97316 = 249/115/22)
  if (tc < 0.5) {
    const k = tc * 2;
    return [
      (37 + (16 - 37) * k) / 255,
      (99 + (185 - 99) * k) / 255,
      (235 + (129 - 235) * k) / 255,
    ];
  }
  const k = (tc - 0.5) * 2;
  return [
    (16 + (249 - 16) * k) / 255,
    (185 + (115 - 185) * k) / 255,
    (129 + (22 - 129) * k) / 255,
  ];
}

function colorForElement(
  element: ResultMeshElement,
  valueMin: number,
  valueMax: number,
  fieldComponent: StressComponent = 'mises',
): [number, number, number] {
  if (element.alive === false) return [0.94, 0.27, 0.27]; // red for deleted
  if (element.partRole === 'projectile') return [0.9, 0.92, 0.94];
  // FM-04a Phase 23 B — when the element carries a stressTensor, the
  // per-component switcher derives the scalar; fall back to `value`
  // when no tensor present (Phase 22 D path).
  const fallback = element.value ?? valueMin;
  const v = element.stressTensor
    ? componentValue(element.stressTensor, fieldComponent, fallback)
    : fallback;
  const t = valueMax > valueMin ? (v - valueMin) / (valueMax - valueMin) : 0;
  return gradientStop(t);
}

export function colorForValueFraction(t: number): [number, number, number] {
  return gradientStop(t);
}

/** Phase 22 B — build node-coordinate map honouring optional
 * deformation magnification AND optional frame interpolation. When
 * `nextFrame` is provided + `tInterp` ∈ (0, 1), node positions blend
 * linearly between the two frames' DEFORMED coordinates (or fall
 * back to undeformed coords when deformed is absent). The
 * `deformationScale` multiplier amplifies the deformed displacement
 * relative to undeformed for visualization on small-strain results. */
export function buildNodeCoords(
  frame: ResultMeshFrame,
  nextFrame: ResultMeshFrame | null | undefined,
  tInterp: number,
  deformationScale: number,
): Map<number, [number, number, number]> {
  const nodeCoords = new Map<number, [number, number, number]>();
  // Index nextFrame nodes by label for blend lookup.
  const nextByLabel = new Map<number, [number, number, number]>();
  if (nextFrame && tInterp > 0) {
    for (const nn of nextFrame.nodes) {
      const p = nn.deformed ?? nn.coordinates;
      if (p && p.length >= 3) {
        nextByLabel.set(nn.label, [p[0], p[1], p[2]]);
      }
    }
  }
  const t = nextFrame ? Math.max(0, Math.min(1, tInterp)) : 0;
  for (const node of frame.nodes) {
    const undef = node.coordinates;
    const def = node.deformed ?? node.coordinates;
    if (!def || def.length < 3) continue;
    const baseX = def[0];
    const baseY = def[1];
    const baseZ = def[2];
    // Magnify deformation relative to undeformed coords when available.
    let x = baseX;
    let y = baseY;
    let z = baseZ;
    if (
      deformationScale !== 1 &&
      undef &&
      undef.length >= 3 &&
      node.deformed &&
      node.deformed.length >= 3
    ) {
      x = undef[0] + (node.deformed[0] - undef[0]) * deformationScale;
      y = undef[1] + (node.deformed[1] - undef[1]) * deformationScale;
      z = undef[2] + (node.deformed[2] - undef[2]) * deformationScale;
    }
    // Blend toward nextFrame when t > 0.
    const nxt = nextByLabel.get(node.label);
    if (nxt && t > 0) {
      x = x + (nxt[0] - x) * t;
      y = y + (nxt[1] - y) * t;
      z = z + (nxt[2] - z) * t;
    }
    nodeCoords.set(node.label, [x, y, z]);
  }
  return nodeCoords;
}

function buildBufferGeometry(
  frame: ResultMeshFrame,
  valueMin: number,
  valueMax: number,
  options: {
    nextFrame?: ResultMeshFrame | null;
    tInterp?: number;
    deformationScale?: number;
    fieldComponent?: StressComponent;
    valueFilter?: ValueFilterState | null;
  } = {},
): {
  geometry: THREE.BufferGeometry;
  bounds: THREE.Box3;
  triangleCount: number;
} {
  const nodeCoords = buildNodeCoords(
    frame,
    options.nextFrame ?? null,
    options.tInterp ?? 0,
    options.deformationScale ?? 1,
  );

  const triangles: Triangle[] = [];
  for (const element of frame.elements) {
    // Phase 23 D — apply value filter (returns true for retain).
    if (!applyValueFilter(element, options.valueFilter ?? null, options.fieldComponent ?? 'mises')) {
      continue;
    }
    const color = colorForElement(
      element,
      valueMin,
      valueMax,
      options.fieldComponent ?? 'mises',
    );
    triangles.push(...elementTriangles(element, nodeCoords, color));
  }

  const positions = new Float32Array(triangles.length * 9);
  const colors = new Float32Array(triangles.length * 9);
  for (let i = 0; i < triangles.length; i++) {
    positions.set(triangles[i].positions, i * 9);
    const [r, g, b] = triangles[i].colorRgb;
    for (let v = 0; v < 3; v++) {
      colors[i * 9 + v * 3 + 0] = r;
      colors[i * 9 + v * 3 + 1] = g;
      colors[i * 9 + v * 3 + 2] = b;
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.computeVertexNormals();

  const bounds = new THREE.Box3();
  bounds.setFromBufferAttribute(geometry.getAttribute('position') as THREE.BufferAttribute);

  return { geometry, bounds, triangleCount: triangles.length };
}

/** FM-04a Phase 23 C — find the closest node in the frame to a
 * world-space point. Used after raycasting to map an intersection
 * point back to a frame node label. Returns null when the frame
 * has no nodes. */
export function findClosestNode(
  frame: ResultMeshFrame,
  worldPoint: [number, number, number],
  nodeCoords: Map<number, [number, number, number]>,
): { label: number; position: [number, number, number]; distance: number } | null {
  let best: { label: number; position: [number, number, number]; distance: number } | null = null;
  for (const node of frame.nodes) {
    const coords = nodeCoords.get(node.label);
    if (!coords) continue;
    const dx = coords[0] - worldPoint[0];
    const dy = coords[1] - worldPoint[1];
    const dz = coords[2] - worldPoint[2];
    const d2 = dx * dx + dy * dy + dz * dz;
    if (best === null || d2 < best.distance) {
      best = {
        label: node.label,
        position: [coords[0], coords[1], coords[2]],
        distance: d2,
      };
    }
  }
  if (best) {
    return { ...best, distance: Math.sqrt(best.distance) };
  }
  return null;
}

/** FM-04a Phase 23 C — find the field value of the element nearest
 * (in connectivity) to the picked node. Walks the frame's elements
 * to find one whose connectivity contains `nodeLabel`; returns its
 * derived scalar via the same component-switcher path. Returns null
 * when no element references this node or the candidate element has
 * no value. */
export function fieldValueAtNode(
  frame: ResultMeshFrame,
  nodeLabel: number,
  fieldComponent: StressComponent,
): number | null {
  for (const element of frame.elements) {
    if (!element.connectivity?.includes(nodeLabel)) continue;
    if (element.stressTensor) {
      return componentValue(element.stressTensor, fieldComponent, element.value ?? 0);
    }
    if (element.value !== undefined) return element.value;
  }
  return null;
}

/** FM-04a Phase 23 D — element value selector for the threshold
 * filter. Uses the same component-switcher path as the coloring
 * (`colorForElement`) so the filter compares against the SAME
 * scalar the reviewer sees on the gradient. */
function elementFilterValue(
  element: ResultMeshElement,
  fieldComponent: StressComponent,
): number | undefined {
  if (element.alive === false) return undefined;
  if (element.partRole === 'projectile') return undefined;
  if (element.stressTensor) {
    return componentValue(
      element.stressTensor,
      fieldComponent,
      element.value ?? 0,
    );
  }
  return element.value;
}

/** FM-04a Phase 23 D — pure-function filter predicate. Returns true
 * when the element should RENDER. Elements with no derivable value
 * (alive=false, projectile, no value, no tensor) ALWAYS render
 * regardless of filter — that's the D:-1 anti-gaming guard. */
export function applyValueFilter(
  element: ResultMeshElement,
  filter: ValueFilterState | null | undefined,
  fieldComponent: StressComponent = 'mises',
): boolean {
  if (!filter) return true;
  const v = elementFilterValue(element, fieldComponent);
  // D:-1: elements without a value are retained.
  if (v === undefined || !Number.isFinite(v)) return true;
  const lo = filter.minValue ?? Number.NEGATIVE_INFINITY;
  const hi = filter.maxValue ?? Number.POSITIVE_INFINITY;
  const inside = v >= lo && v <= hi;
  return filter.mode === 'inside' ? inside : !inside;
}

function detectWebGLSupport(): boolean {
  if (typeof window === 'undefined' || typeof document === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return Boolean(
      canvas.getContext('webgl2') ||
        canvas.getContext('webgl') ||
        canvas.getContext('experimental-webgl'),
    );
  } catch {
    return false;
  }
}

export function ResultMeshWebGLViewport({
  frame,
  valueMin,
  valueMax,
  nextFrame,
  playing = false,
  deformationScale = 1,
  sectionCut = null,
  fieldComponent = 'mises',
  onNodePicked,
  valueFilter = null,
}: ResultMeshWebGLViewportProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    mesh: THREE.Mesh | null;
    clipPlane: THREE.Plane;
    target: THREE.Vector3;
    radius: number;
    azimuth: number;
    elevation: number;
    initialized: boolean;
  } | null>(null);
  const [supported] = useState<boolean>(detectWebGLSupport);
  const [triangleCount, setTriangleCount] = useState<number>(0);
  // Phase 22 B — frame-to-frame animation tInterp state.
  const [animTInterp, setAnimTInterp] = useState<number>(0);
  // Phase 23 C — picked node state for the HUD overlay.
  const [pickedNode, setPickedNode] = useState<PickedNodeInfo | null>(null);

  // Initialise + dispose the three.js context once.
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !supported) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    } catch {
      // Some browsers / jsdom drop WebGL silently — fail fast to the
      // SVG fallback path rendered by the parent.
      return;
    }
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setClearColor(0x020617);
    // FM-04a Phase 22 B — enable local clipping so the section-cut
    // plane can hide one half of the mesh on demand.
    renderer.localClippingEnabled = true;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.001, 10000);
    const ambient = new THREE.AmbientLight(0xffffff, 0.85);
    const directional = new THREE.DirectionalLight(0xffffff, 0.45);
    directional.position.set(1, 1.5, 1);
    scene.add(ambient);
    scene.add(directional);

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height || 360));
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };

    container.appendChild(renderer.domElement);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';
    renderer.domElement.setAttribute('data-testid', 'webgl-canvas');

    stateRef.current = {
      renderer,
      scene,
      camera,
      mesh: null,
      // Inactive clip plane until a sectionCut prop tells us otherwise.
      clipPlane: new THREE.Plane(new THREE.Vector3(1, 0, 0), Infinity),
      target: new THREE.Vector3(0, 0, 0),
      radius: 1,
      azimuth: Math.PI / 4,
      elevation: Math.PI / 6,
      initialized: false,
    };

    resize();
    const observer =
      typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
    observer?.observe(container);
    return () => {
      observer?.disconnect();
      renderer.dispose();
      if (renderer.domElement.parentElement === container) {
        container.removeChild(renderer.domElement);
      }
      stateRef.current = null;
    };
  }, [supported]);

  // Build / rebuild geometry when the selected frame, animation
  // interpolation, magnification, or nextFrame changes.
  useEffect(() => {
    const state = stateRef.current;
    if (!state || !frame) {
      setTriangleCount(0);
      return;
    }
    const { geometry, bounds, triangleCount: count } = buildBufferGeometry(
      frame,
      valueMin,
      valueMax,
      {
        nextFrame: nextFrame ?? null,
        tInterp: animTInterp,
        deformationScale,
        fieldComponent,
        valueFilter,
      },
    );

    if (state.mesh) {
      state.scene.remove(state.mesh);
      state.mesh.geometry.dispose();
      (state.mesh.material as THREE.Material).dispose();
    }

    // Phase 22 B — clip planes wired into the material when a
    // section-cut state is active.
    const clippingPlanes: THREE.Plane[] = [];
    if (sectionCut) {
      const axisIdx = { x: 0, y: 1, z: 2 }[sectionCut.axis];
      const normal = new THREE.Vector3(
        axisIdx === 0 ? 1 : 0,
        axisIdx === 1 ? 1 : 0,
        axisIdx === 2 ? 1 : 0,
      );
      if (sectionCut.showLow) normal.multiplyScalar(-1);
      const dist = sectionCut.showLow ? sectionCut.positionM : -sectionCut.positionM;
      state.clipPlane.normal.copy(normal);
      state.clipPlane.constant = dist;
      clippingPlanes.push(state.clipPlane);
    }

    const material = new THREE.MeshPhongMaterial({
      vertexColors: true,
      flatShading: false,
      side: THREE.DoubleSide,
      shininess: 35,
      clippingPlanes,
      clipShadows: true,
    });
    const mesh = new THREE.Mesh(geometry, material);
    state.scene.add(mesh);
    state.mesh = mesh;

    const center = new THREE.Vector3();
    bounds.getCenter(center);
    const size = new THREE.Vector3();
    bounds.getSize(size);
    const span = Math.max(size.x, size.y, size.z) || 1;
    state.target.copy(center);
    state.radius = span * 2.2;
    if (!state.initialized) {
      state.azimuth = Math.PI / 4;
      state.elevation = Math.PI / 6;
      state.initialized = true;
    }
    setTriangleCount(count);
    renderScene(state);
  }, [frame, valueMin, valueMax, nextFrame, animTInterp, deformationScale, sectionCut, fieldComponent, valueFilter]);

  // Phase 22 B — animation loop. When `playing && nextFrame`, drive
  // `animTInterp` from 0 → 1 over a fixed duration so the parent's
  // setInterval-based frame advance is smoothed by per-frame
  // interpolation. When playing stops or nextFrame disappears, snap
  // back to 0 (i.e. render the source frame, undeformed by blend).
  useEffect(() => {
    if (!playing || !nextFrame) {
      setAnimTInterp(0);
      return;
    }
    let rafId = 0;
    let cancelled = false;
    const startedAt = performance.now();
    // Match the parent setInterval cadence (240ms) so the animation
    // arrives at t=1 around the moment the frame advances.
    const DURATION_MS = 220;
    const tick = () => {
      if (cancelled) return;
      const elapsed = performance.now() - startedAt;
      const t = Math.min(1, elapsed / DURATION_MS);
      setAnimTInterp(t);
      if (t < 1) {
        rafId = requestAnimationFrame(tick);
      }
    };
    rafId = requestAnimationFrame(tick);
    return () => {
      cancelled = true;
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [playing, nextFrame, frame]);

  // Mouse interactions: orbit (left drag), pan (right drag), zoom
  // (wheel). Hand-rolled rather than via three/examples/OrbitControls
  // so the dependency surface stays at vanilla three.
  useEffect(() => {
    const state = stateRef.current;
    if (!state) return;
    const dom = state.renderer.domElement;

    let dragging: 'orbit' | 'pan' | null = null;
    let lastX = 0;
    let lastY = 0;
    let dragStartedAt = { x: 0, y: 0 };
    let totalDragDistance = 0;
    const ROTATE_SPEED = 0.005;
    const PAN_SPEED = 0.0015;
    const ZOOM_FACTOR = 0.12;
    // Phase 23 C — click vs drag threshold (px). A mouseup within
    // this radius of mousedown counts as a click → triggers raycast.
    const CLICK_PX_THRESHOLD = 4;

    const onMouseDown = (e: MouseEvent) => {
      if (e.button === 0) dragging = 'orbit';
      else if (e.button === 2) dragging = 'pan';
      lastX = e.clientX;
      lastY = e.clientY;
      dragStartedAt = { x: e.clientX, y: e.clientY };
      totalDragDistance = 0;
      e.preventDefault();
    };
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      totalDragDistance += Math.abs(dx) + Math.abs(dy);
      if (dragging === 'orbit') {
        state.azimuth -= dx * ROTATE_SPEED;
        state.elevation = Math.max(
          -Math.PI / 2 + 0.01,
          Math.min(Math.PI / 2 - 0.01, state.elevation - dy * ROTATE_SPEED),
        );
      } else {
        const right = new THREE.Vector3()
          .setFromMatrixColumn(state.camera.matrix, 0)
          .multiplyScalar(-dx * state.radius * PAN_SPEED);
        const up = new THREE.Vector3()
          .setFromMatrixColumn(state.camera.matrix, 1)
          .multiplyScalar(dy * state.radius * PAN_SPEED);
        state.target.add(right).add(up);
      }
      renderScene(state);
    };
    const onMouseUp = (e: MouseEvent) => {
      // Phase 23 C — if the mouseup is close to the mousedown (i.e.
      // a click, not a drag), trigger a raycast pick.
      const totalDelta =
        Math.abs(e.clientX - dragStartedAt.x)
        + Math.abs(e.clientY - dragStartedAt.y);
      if (
        e.button === 0
        && totalDelta <= CLICK_PX_THRESHOLD
        && totalDragDistance <= CLICK_PX_THRESHOLD
        && frame
        && state.mesh
      ) {
        const rect = dom.getBoundingClientRect();
        const ndcX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        const ndcY = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        const ray = new THREE.Raycaster();
        ray.setFromCamera(new THREE.Vector2(ndcX, ndcY), state.camera);
        const hits = ray.intersectObject(state.mesh, false);
        if (hits.length > 0) {
          const worldPoint: [number, number, number] = [
            hits[0].point.x,
            hits[0].point.y,
            hits[0].point.z,
          ];
          // Rebuild the same node coord map the geometry build used
          // so we map the world hit back to a frame node label.
          const nodeCoords = buildNodeCoords(
            frame,
            nextFrame ?? null,
            animTInterp,
            deformationScale,
          );
          const closest = findClosestNode(frame, worldPoint, nodeCoords);
          if (closest) {
            const fieldValue = fieldValueAtNode(frame, closest.label, fieldComponent);
            const info: PickedNodeInfo = {
              label: closest.label,
              position: closest.position,
              fieldValue,
            };
            setPickedNode(info);
            onNodePicked?.(info);
          }
        }
      }
      dragging = null;
    };
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 1 + ZOOM_FACTOR : 1 - ZOOM_FACTOR;
      state.radius = Math.max(1e-4, state.radius * factor);
      renderScene(state);
    };
    const onContextMenu = (e: MouseEvent) => e.preventDefault();

    // Phase 23 C — Escape clears the picked node.
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setPickedNode(null);
        onNodePicked?.(null);
      }
    };

    dom.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    dom.addEventListener('wheel', onWheel, { passive: false });
    dom.addEventListener('contextmenu', onContextMenu);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      dom.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      dom.removeEventListener('wheel', onWheel);
      dom.removeEventListener('contextmenu', onContextMenu);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [triangleCount, frame, nextFrame, animTInterp, deformationScale, fieldComponent, onNodePicked]);

  const message = useMemo(() => {
    if (!supported) return 'WebGL not available — falling back to SVG body';
    if (!frame) return 'No frame selected';
    if (triangleCount === 0) return 'No renderable triangles in frame';
    return null;
  }, [supported, frame, triangleCount]);

  return (
    <div
      data-testid="result-mesh-webgl-viewport"
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 280,
        background: '#020617',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      <div
        ref={containerRef}
        data-testid="webgl-canvas-container"
        style={{ width: '100%', height: '100%' }}
      />
      {message && (
        <div
          data-testid="webgl-message"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#94a3b8',
            fontSize: '0.85rem',
            pointerEvents: 'none',
            textAlign: 'center',
            padding: 16,
          }}
        >
          {message}
        </div>
      )}
      <div
        data-testid="webgl-overlay-help"
        style={{
          position: 'absolute',
          left: 12,
          top: 12,
          color: '#94a3b8',
          fontSize: '0.68rem',
          fontFamily:
            'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
          background: 'rgba(2, 6, 23, 0.62)',
          border: '1px solid rgba(148, 163, 184, 0.2)',
          borderRadius: 4,
          padding: '4px 8px',
          letterSpacing: '0.05em',
          pointerEvents: 'none',
        }}
      >
        DRAG · ORBIT  ·  R-DRAG · PAN  ·  WHEEL · ZOOM  ·  CLICK · PROBE  ·  ESC · CLEAR
      </div>
      {pickedNode && (
        <div
          data-testid="webgl-picked-node-hud"
          style={{
            position: 'absolute',
            right: 12,
            top: 12,
            color: '#e2e8f0',
            fontSize: '0.72rem',
            fontFamily:
              'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
            background: 'rgba(2, 6, 23, 0.85)',
            border: '1px solid rgba(96, 165, 250, 0.45)',
            borderRadius: 4,
            padding: '8px 12px',
            lineHeight: 1.45,
            pointerEvents: 'none',
            minWidth: 180,
          }}
        >
          <div
            style={{
              color: '#60a5fa',
              fontSize: '0.62rem',
              fontWeight: 700,
              letterSpacing: '0.08em',
              marginBottom: 4,
            }}
          >
            NODE {pickedNode.label}
          </div>
          <div data-testid="webgl-picked-node-coords">
            x: {pickedNode.position[0].toExponential(3)}
            <br />
            y: {pickedNode.position[1].toExponential(3)}
            <br />
            z: {pickedNode.position[2].toExponential(3)}
          </div>
          {pickedNode.fieldValue !== null && (
            <div
              data-testid="webgl-picked-node-field"
              style={{ marginTop: 4, color: '#fbbf24' }}
            >
              {fieldComponent}: {pickedNode.fieldValue.toExponential(3)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function renderScene(state: NonNullable<typeof stateRefShape>) {
  const { camera, renderer, scene, target, radius, azimuth, elevation } = state;
  const cosE = Math.cos(elevation);
  camera.position.set(
    target.x + radius * cosE * Math.cos(azimuth),
    target.y + radius * Math.sin(elevation),
    target.z + radius * cosE * Math.sin(azimuth),
  );
  camera.lookAt(target);
  renderer.render(scene, camera);
}

// Helper alias used only to type `state` in the standalone render
// function above. Mirrors the shape stored in `stateRef.current`.
declare const stateRefShape:
  | {
      renderer: THREE.WebGLRenderer;
      scene: THREE.Scene;
      camera: THREE.PerspectiveCamera;
      mesh: THREE.Mesh | null;
      clipPlane: THREE.Plane;
      target: THREE.Vector3;
      radius: number;
      azimuth: number;
      elevation: number;
      initialized: boolean;
    }
  | undefined;

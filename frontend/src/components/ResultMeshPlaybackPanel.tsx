import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { Box, Layers, Pause, Play, ShieldAlert } from 'lucide-react';

import {
  summarizeResultMeshPlayback,
  type ResultMeshElement,
  type ResultMeshFrame,
  type ResultMeshNode,
  type ResultMeshPayload,
} from '../resultMeshPlayback';
// FM-04a Phase 20 D — close the Phase 19 D scope-drift the UI agent
// flagged: the legend was added, but the bespoke loading / error /
// empty <div>s in this panel were never migrated to the SSOT
// primitives. Migrating them now closes that finding.
import { EmptyStateCard } from './EmptyStateCard';
import { ErrorCard } from './ErrorCard';
import { SkeletonCard } from './SkeletonCard';
// FM-04a Phase 21 C — three.js WebGL viewport. Reads the same
// `summary.selectedFrame` the SVG panel consumes; the SVG body stays
// as a fallback when WebGL is unavailable or the user toggles to it.
import { ResultMeshWebGLViewport } from './ResultMeshWebGLViewport';

interface ResultMeshPlaybackPanelProps {
  caseId: string | null;
  apiBase: string;
  enabled?: boolean;
}

interface ProjectedPolygon {
  key: string;
  points: string;
  fill: string;
  stroke: string;
  opacity: number;
  order: number;
}

const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 });

export function ResultMeshPlaybackPanel({
  caseId,
  apiBase,
  enabled = true,
}: ResultMeshPlaybackPanelProps) {
  const [result, setResult] = useState<{
    caseId: string;
    payload: ResultMeshPayload | null;
    error: string | null;
  } | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  // FM-04a Phase 21 C — viewport mode. 'webgl' mounts the three.js
  // viewport above the SVG body; 'svg' is the Phase 19 D-and-earlier
  // path (still the test fallback when WebGL is unavailable). Default
  // is 'webgl' so reviewers see the 3D viewport on first open.
  const [viewportMode, setViewportMode] = useState<'webgl' | 'svg'>('webgl');

  const currentResult = result?.caseId === caseId ? result : null;
  const payload = currentResult?.payload ?? null;
  const error = currentResult?.error ?? null;
  const loading = Boolean(enabled && caseId && !currentResult);

  useEffect(() => {
    if (!enabled || !caseId) return;
    const controller = new AbortController();

    fetch(`${apiBase}/visualize/result-mesh/${encodeURIComponent(caseId)}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            response.status === 404
              ? 'result_mesh.json unavailable'
              : `result_mesh.json request failed (${response.status})`,
          );
        }
        return response.json() as Promise<ResultMeshPayload>;
      })
      .then((data) => {
        setResult({ caseId, payload: data, error: null });
        setFrameIndex(0);
        setPlaying(false);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setResult({
          caseId,
          payload: null,
          error: err instanceof Error ? err.message : 'result_mesh.json request failed',
        });
      });

    return () => controller.abort();
  }, [apiBase, caseId, enabled]);

  const summary = useMemo(
    () => (payload ? summarizeResultMeshPlayback(payload, frameIndex) : null),
    [payload, frameIndex],
  );
  const frameCount = summary?.frameCount ?? 0;

  useEffect(() => {
    if (!playing || frameCount <= 1) return;
    const timer = window.setInterval(() => {
      setFrameIndex((current) => (current + 1 >= frameCount ? 0 : current + 1));
    }, 240);
    return () => window.clearInterval(timer);
  }, [frameCount, playing]);

  const projection = useMemo(
    () => buildProjection(summary?.selectedFrame ?? null, summary?.valueMin ?? 0, summary?.valueMax ?? 0),
    [summary],
  );

  const vtuState = readVtuState(payload);

  return (
    <section
      aria-label="OpenRadioss dynamic playback"
      style={{
        height: '100%',
        minHeight: '360px',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        background: 'rgba(2, 6, 23, 0.72)',
        overflow: 'hidden',
        display: 'grid',
        gridTemplateRows: 'auto 1fr',
      }}
    >
      <div
        style={{
          padding: '14px 16px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Box size={18} color="var(--accent)" />
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
              OpenRadioss dynamic
            </div>
            <h3 style={{ margin: 0, fontSize: '1rem' }}>Result mesh playback</h3>
          </div>
        </div>
        <div
          style={{
            color: '#ef4444',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            background: 'rgba(239, 68, 68, 0.08)',
            borderRadius: '999px',
            padding: '5px 10px',
            fontSize: '0.72rem',
            fontWeight: 800,
          }}
        >
          not signed validation
        </div>
      </div>

      {loading ? (
        <div data-testid="result-mesh-loading" style={{ padding: '14px' }}>
          <SkeletonCard lines={4} label="Loading dynamic payload" />
        </div>
      ) : error ? (
        <div data-testid="result-mesh-error" style={{ padding: '14px' }}>
          <ErrorCard
            title="Could not load dynamic payload"
            message={error}
            code="RESULT-MESH-LOAD"
            remediation={[
              'Run the solver for this case via Topbar → Run Solver to produce a result_mesh.json.',
              'Confirm the backend /visualize/result-mesh route responds for this case_id.',
            ]}
          />
        </div>
      ) : summary ? (
        <div
          style={{
            padding: '14px',
            display: 'grid',
            gridTemplateColumns: 'minmax(360px, 1fr) minmax(260px, 340px)',
            gap: '14px',
            minHeight: 0,
          }}
        >
          <div style={{ minHeight: 0, display: 'grid', gridTemplateRows: 'auto 1fr auto', gap: '12px' }}>
            <div
              data-testid="viewport-mode-toggle"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: 6,
                fontSize: '0.7rem',
              }}
            >
              <button
                type="button"
                data-testid="viewport-toggle-webgl"
                onClick={() => setViewportMode('webgl')}
                style={{
                  padding: '4px 10px',
                  borderRadius: 4,
                  border: '1px solid var(--border)',
                  background:
                    viewportMode === 'webgl' ? 'var(--accent)' : 'transparent',
                  color:
                    viewportMode === 'webgl' ? '#000' : 'var(--text-secondary)',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                3D
              </button>
              <button
                type="button"
                data-testid="viewport-toggle-svg"
                onClick={() => setViewportMode('svg')}
                style={{
                  padding: '4px 10px',
                  borderRadius: 4,
                  border: '1px solid var(--border)',
                  background:
                    viewportMode === 'svg' ? 'var(--accent)' : 'transparent',
                  color:
                    viewportMode === 'svg' ? '#000' : 'var(--text-secondary)',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                SVG
              </button>
            </div>
            <div
              style={{
                minHeight: '210px',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                background: '#020617',
                overflow: 'hidden',
                position: 'relative',
              }}
            >
              {viewportMode === 'webgl' ? (
                <ResultMeshWebGLViewport
                  frame={summary.selectedFrame}
                  valueMin={summary.valueMin}
                  valueMax={summary.valueMax}
                />
              ) : (
              <>
              <svg width="100%" height="100%" viewBox="0 0 1000 440" role="img" aria-label="Dynamic result mesh frame">
                <rect x="0" y="0" width="1000" height="440" fill="#020617" />
                {projection.map((polygon) => (
                  <polygon
                    key={polygon.key}
                    points={polygon.points}
                    fill={polygon.fill}
                    stroke={polygon.stroke}
                    strokeWidth="1.4"
                    opacity={polygon.opacity}
                  />
                ))}
              </svg>
              {projection.length === 0 && (
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '0.84rem',
                  }}
                >
                  No renderable mesh frame
                </div>
              )}
              </>
              )}
              {/* FM-04a Phase 19 D — stress-contour color legend
                  (Phase 21 C: now shared by WebGL + SVG viewports).
                  The legend renders OUTSIDE the WebGL/SVG conditional
                  so the gradient annotation stays visible in both
                  modes. Phase 21 C's three.js viewport uses the same
                  blue→green→orange gradient as the SVG projection. */}
              {summary && (
                <div
                  data-testid="stress-contour-legend"
                  style={{
                    position: 'absolute',
                    right: 16,
                    bottom: 16,
                    background: 'rgba(2, 6, 23, 0.78)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: 6,
                    padding: '8px 12px',
                    color: '#e2e8f0',
                    fontSize: '0.7rem',
                    fontFamily:
                      'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                    minWidth: 140,
                  }}
                  aria-label="Field-value color legend"
                >
                  <div style={{ opacity: 0.75, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                    Field value
                  </div>
                  <div
                    style={{
                      height: 8,
                      borderRadius: 4,
                      background:
                        'linear-gradient(to right, #2563eb 0%, #10b981 50%, #f97316 100%)',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>min {formatNumber(summary.valueMin)}</span>
                    <span>max {formatNumber(summary.valueMax)}</span>
                  </div>
                </div>
              )}
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '40px 1fr minmax(140px, auto)',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <button
                type="button"
                aria-label={playing ? 'Pause' : 'Play'}
                title={playing ? 'Pause' : 'Play'}
                onClick={() => setPlaying((current) => !current)}
                disabled={frameCount <= 1}
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  background: frameCount > 1 ? 'var(--accent)' : 'var(--bg-surface)',
                  color: frameCount > 1 ? '#000' : 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: frameCount > 1 ? 'pointer' : 'not-allowed',
                }}
              >
                {playing ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
              </button>
              <input
                aria-label="Dynamic frame"
                type="range"
                min={0}
                max={Math.max(frameCount - 1, 0)}
                value={summary.selectedFrameIndex}
                onChange={(event) => setFrameIndex(Number(event.target.value))}
                disabled={frameCount <= 1}
                style={{ width: '100%' }}
              />
              <div style={{ textAlign: 'right', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                <div style={{ color: 'var(--text-primary)', fontWeight: 800 }}>
                  Frame {summary.selectedFrameIndex + 1}/{Math.max(frameCount, 1)}
                </div>
                <div>{formatNumber(summary.timeMs)} ms</div>
              </div>
            </div>
          </div>

          <div style={{ minHeight: 0, overflowY: 'auto', display: 'grid', gap: '10px', alignContent: 'start' }}>
            <MetricGrid summary={summary} />

            <div style={panelBoxStyle}>
              <div style={panelTitleStyle}>
                <Layers size={15} color="var(--accent)" />
                Model tree
              </div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {summary.modelTree.map((node) => (
                  <div
                    key={node.id ?? `${node.partRole}-${node.partId}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr auto',
                      gap: '8px',
                      borderTop: '1px solid var(--border)',
                      paddingTop: '8px',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 800 }}>
                        {node.label ?? node.partRole ?? 'Part'}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {node.partRole ?? 'unknown'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                      <div>{node.elementCount ?? 0} elems</div>
                      <div>{node.aliveElementCount ?? node.elementCount ?? 0} alive</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={panelBoxStyle}>
              <div style={panelTitleStyle}>
                <ShieldAlert size={15} color="#ef4444" />
                Evidence boundary
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.76rem', lineHeight: 1.45, overflowWrap: 'anywhere' }}>
                {summary.claimBoundary}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', lineHeight: 1.45, marginTop: '8px', overflowWrap: 'anywhere' }}>
                VTU: {vtuState}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div data-testid="result-mesh-empty" style={{ padding: '14px' }}>
          <EmptyStateCard
            headline="No active dynamic payload"
            body="Run an explicit-dynamics solver for this case to populate frames of stress + displacement evolution. Static-only cases will not surface a playback timeline."
            glyph="∅"
          />
        </div>
      )}
    </section>
  );
}

function MetricGrid({ summary }: { summary: NonNullable<ReturnType<typeof summarizeResultMeshPlayback>> }) {
  const rows = [
    ['Nodes', formatInteger(summary.nodeCount)],
    ['Faces', formatInteger(summary.elementCount)],
    ['Projectile', formatInteger(summary.projectileElements)],
    ['Plate', formatInteger(summary.plateElements)],
    ['Deleted', formatInteger(summary.deletedElements)],
    ['Max disp', formatNumber(summary.maxDisplacement)],
    ['Min field', formatNumber(summary.valueMin)],
    ['Max field', formatNumber(summary.valueMax)],
  ];

  return (
    <div style={{ ...panelBoxStyle, padding: '10px' }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 800, marginBottom: '8px' }}>
        {summary.fieldLabel}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '8px' }}>
        {rows.map(([label, value]) => (
          <div key={label} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '8px', minHeight: '50px' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.66rem', fontWeight: 800, textTransform: 'uppercase' }}>
              {label}
            </div>
            <div style={{ color: 'var(--text-primary)', fontSize: '0.9rem', fontWeight: 800, marginTop: '3px' }}>
              {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function buildProjection(frame: ResultMeshFrame | null, valueMin: number, valueMax: number): ProjectedPolygon[] {
  if (!frame) return [];
  const nodeMap = new Map<number, number[]>();
  frame.nodes.forEach((node) => {
    const point = readPoint(node);
    if (point) nodeMap.set(node.label, point);
  });

  const points = Array.from(nodeMap.values());
  const axes = selectProjectionAxes(points);
  const bounds = computeBounds(points, axes);
  if (!bounds) return [];

  const projected = frame.elements
    .filter((element) => (element.connectivity?.length ?? 0) >= 3)
    .map((element, index) => projectElement(element, index, nodeMap, axes, bounds, valueMin, valueMax))
    .filter((polygon): polygon is ProjectedPolygon => Boolean(polygon))
    .sort((a, b) => a.order - b.order);
  return projected;
}

function readPoint(node: ResultMeshNode): number[] | null {
  const point = node.deformed ?? node.coordinates;
  return point && point.length >= 3 ? point : null;
}

function selectProjectionAxes(points: number[][]): [number, number] {
  if (points.length === 0) return [0, 1];
  const ranges = [0, 1, 2].map((axis) => {
    const values = points.map((point) => point[axis]);
    return { axis, range: Math.max(...values) - Math.min(...values) };
  });
  const sorted = ranges.sort((a, b) => b.range - a.range);
  return [sorted[0]?.axis ?? 0, sorted[1]?.axis ?? 1];
}

function computeBounds(points: number[][], axes: [number, number]) {
  if (points.length === 0) return null;
  const xs = points.map((point) => point[axes[0]]);
  const ys = points.map((point) => point[axes[1]]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    minY,
    scale: Math.min(880 / Math.max(maxX - minX, 1e-9), 340 / Math.max(maxY - minY, 1e-9)),
    offsetX: 500 - ((minX + maxX) / 2) * Math.min(880 / Math.max(maxX - minX, 1e-9), 340 / Math.max(maxY - minY, 1e-9)),
    offsetY: 220 + ((minY + maxY) / 2) * Math.min(880 / Math.max(maxX - minX, 1e-9), 340 / Math.max(maxY - minY, 1e-9)),
  };
}

function projectElement(
  element: ResultMeshElement,
  index: number,
  nodeMap: Map<number, number[]>,
  axes: [number, number],
  bounds: NonNullable<ReturnType<typeof computeBounds>>,
  valueMin: number,
  valueMax: number,
): ProjectedPolygon | null {
  const projectedPoints = (element.connectivity ?? [])
    .map((nodeLabel) => nodeMap.get(nodeLabel))
    .filter((point): point is number[] => Boolean(point))
    .map((point) => {
      const x = point[axes[0]] * bounds.scale + bounds.offsetX;
      const y = bounds.offsetY - point[axes[1]] * bounds.scale;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

  if (projectedPoints.length < 3) return null;
  const alive = element.alive !== false;
  const isProjectile = element.partRole === 'projectile';
  return {
    key: `${element.sourceElement ?? element.label ?? index}-${index}`,
    points: projectedPoints.join(' '),
    fill: alive ? colorForElement(element, valueMin, valueMax) : 'rgba(239, 68, 68, 0.28)',
    stroke: isProjectile ? '#f8fafc' : alive ? 'rgba(148, 163, 184, 0.5)' : 'rgba(239, 68, 68, 0.75)',
    opacity: isProjectile ? 0.92 : alive ? 0.86 : 0.5,
    order: isProjectile ? 3 : alive ? 1 : 2,
  };
}

function colorForElement(element: ResultMeshElement, valueMin: number, valueMax: number) {
  if (element.partRole === 'projectile') return '#e5e7eb';
  const value = element.value ?? valueMin;
  const t = valueMax > valueMin ? Math.min(Math.max((value - valueMin) / (valueMax - valueMin), 0), 1) : 0;
  if (t < 0.5) return mixColor('#2563eb', '#10b981', t * 2);
  return mixColor('#10b981', '#f97316', (t - 0.5) * 2);
}

function mixColor(start: string, end: string, t: number) {
  const a = hexToRgb(start);
  const b = hexToRgb(end);
  const mixed = a.map((value, index) => Math.round(value + (b[index] - value) * t));
  return `rgb(${mixed[0]}, ${mixed[1]}, ${mixed[2]})`;
}

function hexToRgb(hex: string): [number, number, number] {
  return [
    Number.parseInt(hex.slice(1, 3), 16),
    Number.parseInt(hex.slice(3, 5), 16),
    Number.parseInt(hex.slice(5, 7), 16),
  ];
}

function readVtuState(payload: ResultMeshPayload | null) {
  const manifest = payload?.artifacts?.vtuManifest;
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) return 'not surfaced';
  const record = manifest as Record<string, unknown>;
  const status = typeof record.status === 'string' ? record.status : 'unknown';
  const path = typeof record.path === 'string' ? record.path : 'vtu_manifest.json';
  return `${status} / ${path}`;
}

function formatNumber(value: number) {
  if (!Number.isFinite(value)) return '0';
  const magnitude = Math.abs(value);
  if (magnitude > 0 && magnitude < 0.001) return value.toExponential(2);
  return numberFormat.format(value);
}

function formatInteger(value: number) {
  return Number.isFinite(value) ? String(Math.trunc(value)) : '0';
}

const panelBoxStyle = {
  border: '1px solid var(--border)',
  borderRadius: '8px',
  background: 'rgba(15, 23, 42, 0.5)',
  padding: '12px',
} satisfies CSSProperties;

const panelTitleStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  color: 'var(--text-primary)',
  fontSize: '0.84rem',
  fontWeight: 800,
  marginBottom: '8px',
} satisfies CSSProperties;

// FM-04a Phase 24 D — multi-node probe list panel.
//
// Renders the pinned-node table next to the WebGL viewport. Each row
// shows the node label, xyz coords in scientific notation, the field
// value (Mises / σ_xx etc — same scalar the gradient is coloring by),
// and a small remove button.
//
// Pin order is preserved — see D:-2 anti-gaming guard in probeList.ts.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { type CSSProperties } from 'react';

import type { PickedNodeInfo } from './viewportRaycaster';
import {
  PROBE_LIST_MAX,
  serializeProbeListAsCsv,
  buildDiffPairs,
  type ProbeListState,
  probeCount,
} from './probeList';

export interface ProbeListPanelProps {
  state: ProbeListState;
  /** Optional active pick that hasn't been pinned yet. Shown in the
   * "Pin current" affordance row when present. */
  activePick?: PickedNodeInfo | null;
  /** Called when the user clicks the "+ Pin current pick" button. */
  onPinActive?: () => void;
  /** Called with the node label of the row whose remove button was
   * clicked. */
  onRemove?: (label: number) => void;
  /** Called when the user clicks the "Clear all" button. */
  onClearAll?: () => void;
  /** Optional unit suffix appended to field values (default Pa). */
  fieldUnits?: string;
  /** FM-04a Phase 25 D — optional CSV export handler. When provided
   * (and the list is non-empty), an "Export CSV" button appears in
   * the panel header. Phase 25 D wires the default download flow at
   * the parent; this prop accepts an override for testing. */
  onExportCsv?: (csv: string) => void;
}

function formatScientific(value: number): string {
  if (!Number.isFinite(value)) return '—';
  if (value === 0) return '0';
  return value.toExponential(2);
}

/** FM-04a Phase 26 C — Δ formatter for the diff column.
 *
 * `null` → "—" (baseline itself, or unavailable due to null
 *           fieldValue on either side)
 * 0      → "0" (no sign-prefix wart)
 * +Δ     → "+1.23e+4"
 * −Δ     → "−1.23e+4"   (Unicode minus, not hyphen-minus — visually
 *           distinguishable from font-rendering hyphens)
 */
function formatDiff(value: number | null): string {
  if (value === null) return '—';
  if (!Number.isFinite(value)) return '—';
  if (value === 0) return '0';
  const mag = Math.abs(value).toExponential(2);
  return value > 0 ? `+${mag}` : `−${mag}`;
}

export function ProbeListPanel({
  state,
  activePick,
  onPinActive,
  onRemove,
  onClearAll,
  fieldUnits = 'Pa',
  onExportCsv,
}: ProbeListPanelProps) {
  const count = probeCount(state);
  const pinDisabled =
    !activePick ||
    state.entries.some((e) => e.label === activePick.label) ||
    count >= PROBE_LIST_MAX;
  const csvHandler = onExportCsv ?? defaultCsvExport;

  return (
    <div data-testid="probe-list-panel" style={STYLES.panel}>
      <div style={STYLES.header}>
        <div>
          <div style={STYLES.label}>Probe list</div>
          <div data-testid="probe-list-count" style={STYLES.count}>
            {count} / {PROBE_LIST_MAX} pinned
          </div>
        </div>
        {count > 0 && (
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              type="button"
              data-testid="probe-export-csv"
              onClick={() => csvHandler(serializeProbeListAsCsv(state))}
              style={STYLES.exportButton}
              aria-label="Export probe list to CSV"
            >
              Export CSV
            </button>
            <button
              type="button"
              data-testid="probe-clear-all"
              onClick={() => onClearAll?.()}
              style={STYLES.clearAllButton}
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {activePick && (
        <div style={STYLES.activeRow}>
          <div>
            <div style={STYLES.activeLabel}>Current pick</div>
            <div style={STYLES.activeNode}>
              Node {activePick.label}
            </div>
          </div>
          <button
            type="button"
            data-testid="probe-pin-active"
            onClick={() => onPinActive?.()}
            disabled={pinDisabled}
            style={{
              ...STYLES.pinButton,
              opacity: pinDisabled ? 0.5 : 1,
              cursor: pinDisabled ? 'not-allowed' : 'pointer',
            }}
            aria-disabled={pinDisabled}
          >
            + Pin
          </button>
        </div>
      )}

      {count === 0 ? (
        <div data-testid="probe-list-empty" style={STYLES.empty}>
          No pinned probes. Click a node in the viewport, then "+ Pin".
        </div>
      ) : (
        (() => {
          // FM-04a Phase 26 C — diff column is rendered only when
          // the list has ≥2 entries (a baseline + something to
          // compare). With a single entry the column would be
          // entirely null and just adds visual noise.
          const showDiff = state.entries.length >= 2;
          const diffPairs = buildDiffPairs(state);
          return (
            <table style={STYLES.table} data-testid="probe-list-table">
              <thead>
                <tr>
                  <th style={STYLES.th}>Node</th>
                  <th style={STYLES.th}>X (m)</th>
                  <th style={STYLES.th}>Y (m)</th>
                  <th style={STYLES.th}>Z (m)</th>
                  <th style={STYLES.th}>Value ({fieldUnits})</th>
                  {showDiff && (
                    <th
                      style={STYLES.th}
                      data-testid="probe-diff-header"
                      title="Δ vs first-pinned probe (baseline)"
                    >
                      Δ vs #1
                    </th>
                  )}
                  <th style={STYLES.th}></th>
                </tr>
              </thead>
              <tbody>
                {diffPairs.map((pair, index) => {
                  const { entry, diff, isBaseline } = pair;
                  return (
                    <tr key={entry.label} data-testid={`probe-row-${index}`}>
                      <td
                        data-testid={`probe-row-${index}-label`}
                        style={STYLES.td}
                      >
                        {entry.label}
                        {isBaseline && showDiff && (
                          <span
                            data-testid={`probe-row-${index}-baseline-tag`}
                            style={STYLES.baselineTag}
                            aria-label="baseline probe"
                          >
                            base
                          </span>
                        )}
                      </td>
                      <td style={STYLES.tdMono}>{formatScientific(entry.position[0])}</td>
                      <td style={STYLES.tdMono}>{formatScientific(entry.position[1])}</td>
                      <td style={STYLES.tdMono}>{formatScientific(entry.position[2])}</td>
                      <td style={STYLES.tdMono}>
                        {entry.fieldValue === null ? '—' : formatScientific(entry.fieldValue)}
                      </td>
                      {showDiff && (
                        <td
                          style={STYLES.tdMono}
                          data-testid={`probe-row-${index}-diff`}
                        >
                          {formatDiff(diff)}
                        </td>
                      )}
                      <td style={STYLES.td}>
                        <button
                          type="button"
                          data-testid={`probe-remove-${entry.label}`}
                          onClick={() => onRemove?.(entry.label)}
                          style={STYLES.removeButton}
                          aria-label={`Remove probe for node ${entry.label}`}
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          );
        })()
      )}
    </div>
  );
}

/** Default CSV download flow — creates a Blob URL and triggers a
 * synthetic <a download> click. Skipped when window/document is
 * unavailable (SSR / test environments). Tests pass `onExportCsv`
 * to inject a stub instead of invoking this. */
function defaultCsvExport(csv: string): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  try {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    a.download = `probe-list-${stamp}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch {
    /* swallow — CSV export is a best-effort affordance */
  }
}

const STYLES: Record<string, CSSProperties> = {
  panel: {
    background: 'rgba(15, 23, 42, 0.88)',
    border: '1px solid rgba(148, 163, 184, 0.25)',
    borderRadius: 8,
    padding: '12px 14px',
    color: '#e2e8f0',
    fontSize: '0.8rem',
    width: '100%',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  label: {
    fontSize: '0.7rem',
    fontWeight: 800,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  count: {
    fontSize: '0.72rem',
    color: '#cbd5e1',
    marginTop: 2,
  },
  clearAllButton: {
    background: 'transparent',
    border: '1px solid rgba(148, 163, 184, 0.35)',
    color: '#cbd5e1',
    borderRadius: 4,
    padding: '3px 8px',
    fontSize: '0.7rem',
    cursor: 'pointer',
  },
  exportButton: {
    background: 'rgba(37, 99, 235, 0.18)',
    border: '1px solid rgba(37, 99, 235, 0.45)',
    color: '#93c5fd',
    borderRadius: 4,
    padding: '3px 8px',
    fontSize: '0.7rem',
    cursor: 'pointer',
    fontWeight: 600,
  },
  activeRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 10px',
    background: 'rgba(37, 99, 235, 0.18)',
    borderRadius: 5,
    marginBottom: 8,
    fontSize: '0.78rem',
  },
  activeLabel: {
    fontSize: '0.65rem',
    color: '#93c5fd',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  activeNode: {
    fontWeight: 600,
    color: '#e0e7ff',
  },
  pinButton: {
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: 4,
    padding: '4px 12px',
    fontWeight: 600,
    fontSize: '0.72rem',
  },
  empty: {
    color: '#94a3b8',
    fontSize: '0.74rem',
    fontStyle: 'italic',
    padding: '12px 6px',
    textAlign: 'center',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontFamily: 'ui-monospace, SFMono-Regular, monospace',
  },
  th: {
    textAlign: 'left',
    padding: '4px 6px',
    color: '#94a3b8',
    fontSize: '0.65rem',
    textTransform: 'uppercase',
    borderBottom: '1px solid rgba(148, 163, 184, 0.2)',
  },
  td: {
    padding: '5px 6px',
    fontSize: '0.74rem',
    color: '#e2e8f0',
    borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
  },
  tdMono: {
    padding: '5px 6px',
    fontSize: '0.72rem',
    color: '#cbd5e1',
    borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
    fontFamily: 'ui-monospace, SFMono-Regular, monospace',
  },
  removeButton: {
    background: 'transparent',
    border: '1px solid rgba(148, 163, 184, 0.35)',
    color: '#fca5a5',
    borderRadius: 3,
    width: 22,
    height: 22,
    padding: 0,
    fontSize: '0.9rem',
    lineHeight: 1,
    cursor: 'pointer',
  },
  baselineTag: {
    display: 'inline-block',
    marginLeft: 6,
    padding: '0 6px',
    background: 'rgba(37, 99, 235, 0.22)',
    color: '#93c5fd',
    border: '1px solid rgba(37, 99, 235, 0.4)',
    borderRadius: 3,
    fontSize: '0.58rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
    verticalAlign: 'middle',
  },
};

// FM-04a Phase 29 B — uniform SectionFrame primitive with
// collapsible header.
//
// Closes the Phase 28 UI-audit gap "no collapse/expand on 7 trust
// sections; industrial reviewer tools default to collapsible
// accordions." Renders one trust section with a clickable header
// containing the chevron + icon + title + (optional) item-count
// summary, and a collapsible body of label/value/detail rows.
//
// Anti-gaming guards:
//   B:-1: prefers-reduced-motion: reduce disables the chevron
//         rotation transition (the chevron still rotates structurally
//         so the user can see WHICH state it's in; only the
//         animation is suppressed).
//   C:-1: storage key includes the storageKey verbatim — no
//         cross-section bleed.
//   D:-1: default is EXPANDED. Toggle persists to localStorage so
//         reviewer's choice survives reloads.
//   E:-1: corrupted/malformed localStorage value → default expanded
//         (per loadSectionCollapsed contract).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import { ChevronDown } from 'lucide-react';

import type { OperatorStatusItem, OperatorStatusSection } from '../types/AppTypes';
import {
  loadSectionCollapsed,
  saveSectionCollapsed,
} from './sectionCollapseStorage';

export interface SectionFrameProps {
  section: OperatorStatusSection;
  /** Stable identifier for localStorage key. Should be URL-safe
   * (no spaces; lowercase kebab-case recommended). */
  storageKey: string;
  /** Initial collapsed state if no persisted value exists.
   * Defaults to `false` (expanded). D:-1 additive guard. */
  defaultCollapsed?: boolean;
  /** Optional forced-collapsed override (for tests / settings UI). */
  forceCollapsed?: boolean;
  /** Optional callback for telemetry / parent state mirror. */
  onCollapsedChange?: (collapsed: boolean) => void;
}

/** Resolve tone → text color (matches OperatorStatusPanel's palette). */
function toneColor(tone?: OperatorStatusItem['tone']): string {
  if (tone === 'accent') return 'var(--accent)';
  if (tone === 'warning') return '#f59e0b';
  if (tone === 'danger') return '#ef4444';
  return 'var(--text-primary)';
}

export function SectionFrame({
  section,
  storageKey,
  defaultCollapsed = false,
  forceCollapsed,
  onCollapsedChange,
}: SectionFrameProps) {
  // Initialize from localStorage; fall back to defaultCollapsed if no
  // persisted value. Synchronous initializer so the first render is
  // already in the correct state (no flash).
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (forceCollapsed !== undefined) return forceCollapsed;
    const persisted = loadSectionCollapsed(storageKey);
    return persisted !== null ? persisted : defaultCollapsed;
  });

  // When the forceCollapsed prop changes, mirror it.
  useEffect(() => {
    if (forceCollapsed !== undefined) setCollapsed(forceCollapsed);
  }, [forceCollapsed]);

  const handleToggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      saveSectionCollapsed(storageKey, next);
      onCollapsedChange?.(next);
      return next;
    });
  }, [storageKey, onCollapsedChange]);

  // Item count summary shown in the collapsed-header state.
  const itemCount = section.items.length;

  return (
    <div
      data-testid={`section-frame-${storageKey}`}
      data-collapsed={collapsed ? 'true' : 'false'}
      style={STYLES.card}
    >
      <button
        type="button"
        data-testid={`section-frame-${storageKey}-toggle`}
        aria-expanded={!collapsed}
        aria-controls={`section-frame-${storageKey}-body`}
        onClick={handleToggle}
        style={STYLES.header}
      >
        <ChevronDown
          size={14}
          aria-hidden="true"
          data-testid={`section-frame-${storageKey}-chevron`}
          style={{
            ...STYLES.chevron,
            transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          }}
          className="fm04a-section-frame-chevron"
        />
        <span style={STYLES.icon}>{section.icon}</span>
        <span style={STYLES.title}>{section.title}</span>
        {collapsed && (
          <span
            data-testid={`section-frame-${storageKey}-count`}
            style={STYLES.count}
          >
            {itemCount} {itemCount === 1 ? 'item' : 'items'}
          </span>
        )}
      </button>
      <div
        id={`section-frame-${storageKey}-body`}
        role="region"
        aria-label={`${section.title} details`}
        data-testid={`section-frame-${storageKey}-body`}
        hidden={collapsed}
        style={collapsed ? { display: 'none' } : STYLES.body}
      >
        {section.items.map((item: OperatorStatusItem) => (
          <div
            key={`${section.title}-${item.label}`}
            data-testid={`section-frame-${storageKey}-row-${item.label}`}
            style={STYLES.row}
          >
            <div style={STYLES.rowLabel}>{item.label}</div>
            <div style={{ ...STYLES.rowValue, color: toneColor(item.tone) }}>
              {item.value}
            </div>
            {item.detail && (
              <div style={STYLES.rowDetail}>{item.detail}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

const STYLES: Record<string, CSSProperties> = {
  card: {
    background: 'rgba(15, 23, 42, 0.48)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: 14,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    width: '100%',
    background: 'transparent',
    border: 'none',
    padding: 0,
    margin: 0,
    color: 'var(--text-primary)',
    fontSize: '0.86rem',
    fontWeight: 800,
    cursor: 'pointer',
    textAlign: 'left',
  },
  chevron: {
    color: 'var(--text-secondary)',
    flex: '0 0 auto',
  },
  icon: {
    color: 'var(--accent)',
    display: 'flex',
    flex: '0 0 auto',
  },
  title: {
    flex: '1 1 auto',
  },
  count: {
    color: 'var(--text-muted)',
    fontSize: '0.7rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    flex: '0 0 auto',
  },
  body: {
    display: 'grid',
    gap: 9,
    marginTop: 10,
  },
  row: {
    borderTop: '1px solid var(--border)',
    paddingTop: 9,
  },
  rowLabel: {
    fontSize: '0.66rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    fontWeight: 700,
    marginBottom: 4,
  },
  rowValue: {
    fontSize: '0.82rem',
    fontWeight: 650,
    lineHeight: 1.35,
    overflowWrap: 'anywhere',
  },
  rowDetail: {
    color: 'var(--text-secondary)',
    fontSize: '0.72rem',
    lineHeight: 1.35,
    marginTop: 4,
    overflowWrap: 'anywhere',
  },
};

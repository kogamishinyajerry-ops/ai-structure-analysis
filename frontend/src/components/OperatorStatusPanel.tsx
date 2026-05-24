// FM-04a Phase 22 C — extracted out of App.tsx as part of the
// LOC-discipline trajectory. Renders the Validation & Trust Center
// header strip + sections + Golden-sample queue. Pure-presentational
// component; all state is owned by the App composition root.
//
// FM-04a Phase 29 B — per-section rendering delegated to the
// SectionFrame primitive (collapsible accordion + uniform visual
// vocabulary). The strip + golden-sample queue still inlined here.
// Per-section collapse state lives in localStorage; storage keys
// are derived from the section title (lowercased / kebabed).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { ShieldAlert } from 'lucide-react';
import type {
  GoldenSampleQueueItem,
  OperatorStatusItem,
  OperatorStatusSection,
} from '../types/AppTypes';
import { installPolishStyles } from './polishStyles';
import { SectionFrame } from './SectionFrame';
import { InContextHint } from './InContextHint';
import { useEffect } from 'react';

/** Derive a stable per-section storage key from the section title.
 * `Validation & Reference` → `validation-reference`. */
export function sectionStorageKey(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export function OperatorStatusPanel({
  strip,
  sections,
  goldenSamples,
}: {
  strip: OperatorStatusItem[];
  sections: OperatorStatusSection[];
  goldenSamples: GoldenSampleQueueItem[];
}) {
  // Phase 29 B — ensure the polish stylesheet (which now carries
  // the chevron-rotation transition rule) is installed.
  useEffect(() => {
    installPolishStyles();
  }, []);
  const toneColor = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'var(--accent)';
    if (tone === 'warning') return '#f59e0b';
    if (tone === 'danger') return '#ef4444';
    return 'var(--text-primary)';
  };

  const toneBackground = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'rgba(16, 185, 129, 0.08)';
    if (tone === 'warning') return 'rgba(245, 158, 11, 0.08)';
    if (tone === 'danger') return 'rgba(239, 68, 68, 0.08)';
    return 'rgba(15, 23, 42, 0.55)';
  };

  const toneBorder = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'rgba(16, 185, 129, 0.35)';
    if (tone === 'warning') return 'rgba(245, 158, 11, 0.35)';
    if (tone === 'danger') return 'rgba(239, 68, 68, 0.35)';
    return 'var(--border)';
  };

  return (
    <section className="glass-panel" style={{ padding: '18px 20px', marginBottom: '24px' }} aria-label="Validation and trust center">
      <InContextHint
        hintId="operator-status"
        label="Workbench state"
        text="This panel tracks the live solve and trust state. If the log connection drops mid-run, you'll get a recovery card with a Retry."
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>Validation & Trust Center</div>
          <h2 style={{ fontSize: '1.1rem', margin: '4px 0 0 0' }}>Evidence-first workbench state</h2>
        </div>
        <div style={{ color: '#ef4444', fontSize: '0.78rem', fontWeight: 800, border: '1px solid rgba(239, 68, 68, 0.35)', borderRadius: '999px', padding: '5px 10px', background: 'rgba(239, 68, 68, 0.08)' }}>
          not signed validation
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginBottom: '18px' }}>
        {strip.map((item) => (
          <div key={item.label} style={{ background: toneBackground(item.tone), border: `1px solid ${toneBorder(item.tone)}`, borderRadius: '8px', padding: '12px', minHeight: '78px' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>{item.label}</div>
            <div style={{ color: toneColor(item.tone), fontSize: '0.88rem', fontWeight: 650, lineHeight: 1.35, overflowWrap: 'anywhere' }}>{item.value}</div>
            {item.detail && <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{item.detail}</div>}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
        {sections.map((section) => (
          <SectionFrame
            key={section.title}
            section={section}
            storageKey={sectionStorageKey(section.title)}
          />
        ))}
      </div>

      <div style={{ marginTop: '14px', background: 'rgba(15, 23, 42, 0.48)', border: '1px solid var(--border)', borderRadius: '8px', padding: '14px' }}>
        <div style={{ fontSize: '0.86rem', fontWeight: 800, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} color="var(--accent)" />
          Golden Sample Review Queue
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
          {goldenSamples.map((sample) => (
            <div key={sample.caseId} style={{ border: `1px solid ${toneBorder(sample.tone)}`, background: toneBackground(sample.tone), borderRadius: '8px', padding: '12px', minHeight: '106px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <div style={{ color: 'var(--text-primary)', fontWeight: 800, fontSize: '0.82rem' }}>{sample.caseId}</div>
                <div style={{ color: toneColor(sample.tone), fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase' }}>{sample.status}</div>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.74rem', lineHeight: 1.35, marginBottom: '6px' }}>{sample.name}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.35, overflowWrap: 'anywhere' }}>{sample.reason}</div>
              <div style={{ color: toneColor(sample.tone), fontSize: '0.7rem', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{sample.failurePatternRef}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

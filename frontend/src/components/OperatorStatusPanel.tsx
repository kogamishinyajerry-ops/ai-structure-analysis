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
  // FM-04a Phase 42: status hues route through the --warn-400 / --danger-400
  // tokens (text), and the bg/border tints use the SAME token RGB so each tone
  // stays self-consistent (warn #fbbf24 = 251,191,36 · danger #f87171 = 248,113,113).
  const toneColor = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'var(--accent)';
    if (tone === 'warning') return 'var(--warn-400)';
    if (tone === 'danger') return 'var(--danger-400)';
    return 'var(--text-primary)';
  };

  const toneBackground = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'var(--accent-glow)';
    if (tone === 'warning') return 'rgba(179, 121, 26, 0.10)';
    if (tone === 'danger') return 'rgba(197, 69, 59, 0.10)';
    return 'var(--c-50)';
  };

  const toneBorder = (tone?: OperatorStatusItem['tone']) => {
    if (tone === 'accent') return 'var(--border-focus)';
    if (tone === 'warning') return 'rgba(179, 121, 26, 0.30)';
    if (tone === 'danger') return 'rgba(197, 69, 59, 0.30)';
    return 'var(--border)';
  };

  return (
    <section className="glass-panel" style={{ padding: '18px var(--sp-5)', marginBottom: 'var(--sp-6)' }} aria-label="Validation and trust center">
      <InContextHint
        hintId="operator-status"
        label="Workbench state"
        text="This panel tracks the live solve and trust state. If the log connection drops mid-run, you'll get a recovery card with a Retry."
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--sp-4)', marginBottom: 'var(--sp-4)', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>Validation & Trust Center</div>
          <h2 style={{ fontSize: '1.1rem', margin: 'var(--sp-1) 0 0 0' }}>Evidence-first workbench state</h2>
        </div>
        <div style={{ color: 'var(--danger-400)', fontSize: '0.78rem', fontWeight: 800, border: '1px solid rgba(197, 69, 59, 0.30)', borderRadius: '999px', padding: '5px 10px', background: 'rgba(197, 69, 59, 0.10)' }}>
          not signed validation
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginBottom: '18px' }}>
        {strip.map((item) => (
          <div key={item.label} style={{ background: toneBackground(item.tone), border: `1px solid ${toneBorder(item.tone)}`, borderRadius: 'var(--r-sm)', padding: 'var(--sp-3)', minHeight: '78px' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>{item.label}</div>
            <div style={{ color: toneColor(item.tone), fontSize: '0.88rem', fontWeight: 650, lineHeight: 1.35, overflowWrap: 'anywhere' }}>{item.value}</div>
            {item.detail && <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--fs-xs)', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{item.detail}</div>}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--sp-3)' }}>
        {sections.map((section) => (
          <SectionFrame
            key={section.title}
            section={section}
            storageKey={sectionStorageKey(section.title)}
          />
        ))}
      </div>

      <div style={{ marginTop: '14px', background: 'var(--c-50)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '14px' }}>
        <div style={{ fontSize: '0.86rem', fontWeight: 800, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
          <ShieldAlert size={16} color="var(--accent)" />
          Golden Sample Review Queue
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
          {goldenSamples.map((sample) => (
            <div key={sample.caseId} style={{ border: `1px solid ${toneBorder(sample.tone)}`, background: toneBackground(sample.tone), borderRadius: 'var(--r-sm)', padding: 'var(--sp-3)', minHeight: '106px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: '6px' }}>
                <div style={{ color: 'var(--text-primary)', fontWeight: 800, fontSize: 'var(--fs-sm)' }}>{sample.caseId}</div>
                <div style={{ color: toneColor(sample.tone), fontWeight: 800, fontSize: '0.68rem', textTransform: 'uppercase' }}>{sample.status}</div>
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.74rem', lineHeight: 1.35, marginBottom: '6px' }}>{sample.name}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--fs-xs)', lineHeight: 1.35, overflowWrap: 'anywhere' }}>{sample.reason}</div>
              <div style={{ color: toneColor(sample.tone), fontSize: '0.7rem', lineHeight: 1.35, marginTop: '6px', overflowWrap: 'anywhere' }}>{sample.failurePatternRef}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

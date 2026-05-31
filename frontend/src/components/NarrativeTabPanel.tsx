// FM-04a Phase 22 C — Narrative tab body extracted out of App.tsx
// as part of the LOC-discipline trajectory. Renders the Design
// Auditor Insight markdown surface + Export PDF button. Pure-
// presentational; downloadPDFReport is provided by the App
// composition root.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import { BookOpen, Download } from 'lucide-react';
import type { ReportData } from '../types/AppTypes';

export interface NarrativeTabPanelProps {
  report: ReportData;
  onDownloadPDF: () => void | Promise<void>;
}

export function NarrativeTabPanel({ report, onDownloadPDF }: NarrativeTabPanelProps) {
  return (
    <div
      data-testid="narrative-tab-panel"
      style={{ padding: 'var(--sp-10)', color: 'var(--text-secondary)' }}
      className="report-markdown"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--sp-6)',
          paddingBottom: 'var(--sp-4)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
          <BookOpen size={20} color="var(--accent)" />
          <h2 style={{ margin: 0 }}>Design Auditor Insight</h2>
        </div>
        <button
          data-testid="narrative-export-pdf"
          onClick={onDownloadPDF}
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            color: 'var(--accent)',
            padding: '6px 14px',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-2)',
          }}
        >
          <Download size={14} /> Export PDF Document
        </button>
      </div>
      <div
        data-testid="narrative-markdown-body"
        dangerouslySetInnerHTML={{ __html: report.markdown.replace(/\n/g, '<br/>') }}
      />
    </div>
  );
}

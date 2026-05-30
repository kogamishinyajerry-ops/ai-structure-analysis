import { Activity, Box, ClipboardCheck, ShieldAlert } from 'lucide-react';

import {
  buildBulletPlateBlueprintSummary,
  bulletPlateBlueprint,
  evidenceRefsForAnchor,
  type BulletPlateBlueprintAnchor,
  type BulletPlateBlueprintSlice,
  type BulletPlateEvidenceRef,
} from '../bulletPlateBlueprint';

const anchorTone = (status: BulletPlateBlueprintAnchor['status']) => {
  if (status === 'frontend_surface') return 'var(--accent)';
  if (status === 'evidence_required') return 'var(--warn-400)';
  return 'var(--text-secondary)';
};

const sliceTone = (status: BulletPlateBlueprintSlice['status']) =>
  status === 'started' || status === 'available' ? 'var(--accent)' : 'var(--warn-400)';

const evidenceTone = (status: BulletPlateEvidenceRef['status']) => {
  if (status === 'available') return 'var(--accent)';
  if (status === 'disabled') return 'var(--text-secondary)';
  return 'var(--warn-400)';
};

export function BulletPlateBlueprintPanel() {
  const summary = buildBulletPlateBlueprintSummary();

  return (
    <section
      className="glass-panel"
      aria-label="Bullet-plate target blueprint"
      style={{
        padding: '18px',
        marginBottom: '24px',
        display: 'grid',
        gridTemplateColumns: 'minmax(360px, 1.35fr) minmax(300px, 0.85fr)',
        gap: '16px',
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            marginBottom: '14px',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Box size={18} color="var(--accent)" />
            <div>
              <div
                style={{
                  fontSize: '0.7rem',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  fontWeight: 800,
                }}
              >
                FM-04a blueprint memory
              </div>
              <h3 style={{ margin: '3px 0 0 0', fontSize: '1rem' }}>
                {bulletPlateBlueprint.chineseTitle}
              </h3>
            </div>
          </div>
          <div
            style={{
              border: '1px solid rgba(179, 121, 26, 0.30)',
              color: 'var(--warn-400)',
              background: 'rgba(179, 121, 26, 0.10)',
              borderRadius: '999px',
              padding: '5px 10px',
              fontSize: '0.72rem',
              fontWeight: 800,
            }}
          >
            {summary.claimTier}
          </div>
        </div>

        <BlueprintSchematic />
      </div>

      <div style={{ display: 'grid', gap: '12px', alignContent: 'start' }}>
        <div
          style={{
            border: '1px solid rgba(197, 69, 59, 0.30)',
            background: 'rgba(197, 69, 59, 0.10)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <ShieldAlert size={15} color="var(--danger-400)" />
            <div style={{ fontSize: '0.76rem', color: 'var(--danger-400)', fontWeight: 800 }}>
              Claim boundary
            </div>
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.45 }}>
            {summary.allowedClaim}
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '8px',
          }}
        >
          <Metric label="anchors" value={summary.anchorCount.toString()} />
          <Metric label="covered" value={`${summary.coveredAnchorCount}/${summary.anchorCount}`} />
          <Metric label="evidence" value={`${summary.availableEvidenceCount}/${summary.evidenceCount}`} />
          <Metric label="started" value={summary.startedSlices.toString()} />
          <Metric label="blockers" value={summary.blockerCount.toString()} tone="var(--warn-400)" />
        </div>

        <div
          style={{
            border: '1px solid var(--border)',
            background: 'var(--c-50)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 800 }}>
            Evidence case
          </div>
          <div style={{ color: 'var(--accent)', fontSize: '0.78rem', fontWeight: 800, marginTop: '6px', overflowWrap: 'anywhere' }}>
            {summary.evidenceCaseId}
          </div>
        </div>

        <div
          style={{
            border: '1px solid var(--border)',
            background: 'var(--c-50)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <ClipboardCheck size={15} color="var(--accent)" />
            <div style={{ fontSize: '0.78rem', fontWeight: 800 }}>Blueprint anchors</div>
          </div>
          <div style={{ display: 'grid', gap: '9px' }}>
            {bulletPlateBlueprint.visualAnchors.map((anchor) => (
              <div key={anchor.id} style={{ borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
                <div style={{ color: anchorTone(anchor.status), fontSize: '0.78rem', fontWeight: 800 }}>
                  {anchor.chineseLabel} / {anchor.label}
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.4, marginTop: '3px' }}>
                  {anchor.evidenceRole}
                </div>
                <EvidenceList evidenceRefs={evidenceRefsForAnchor(anchor.id)} />
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            border: '1px solid var(--border)',
            background: 'var(--c-50)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <Activity size={15} color="var(--accent)" />
            <div style={{ fontSize: '0.78rem', fontWeight: 800 }}>Implementation slices</div>
          </div>
          <div style={{ display: 'grid', gap: '8px' }}>
            {bulletPlateBlueprint.implementationSlices.map((slice) => (
              <div key={slice.id} style={{ borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
                <div style={{ color: sliceTone(slice.status), fontSize: '0.78rem', fontWeight: 800 }}>
                  {slice.status.replace('_', ' ')}
                </div>
                <div style={{ color: 'var(--text-primary)', fontSize: '0.76rem', lineHeight: 1.35, marginTop: '3px' }}>
                  {slice.label}
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.7rem', lineHeight: 1.35, marginTop: '3px' }}>
                  {slice.verification}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function EvidenceList({ evidenceRefs }: { evidenceRefs: BulletPlateEvidenceRef[] }) {
  if (evidenceRefs.length === 0) {
    return (
      <div style={{ color: 'var(--warn-400)', fontSize: '0.68rem', lineHeight: 1.35, marginTop: '6px' }}>
        Evidence not indexed yet.
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: '5px', marginTop: '7px' }}>
      {evidenceRefs.map((evidence) => (
        <div key={evidence.id} style={{ borderLeft: `2px solid ${evidenceTone(evidence.status)}`, paddingLeft: '8px' }}>
          <div style={{ color: evidenceTone(evidence.status), fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase' }}>
            {evidence.status} · {evidence.sourceKind.replace(/_/g, ' ')}
          </div>
          <div style={{ color: 'var(--text-primary)', fontSize: '0.7rem', lineHeight: 1.35, marginTop: '2px' }}>
            {evidence.label}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.66rem', lineHeight: 1.35, marginTop: '2px', overflowWrap: 'anywhere' }}>
            {evidence.path}
          </div>
        </div>
      ))}
    </div>
  );
}

function Metric({ label, value, tone = 'var(--accent)' }: { label: string; value: string; tone?: string }) {
  return (
    <div
      style={{
        border: '1px solid var(--border)',
        background: 'var(--c-50)',
        borderRadius: '8px',
        padding: '10px',
        minHeight: '64px',
      }}
    >
      <div style={{ color: 'var(--text-muted)', fontSize: '0.64rem', textTransform: 'uppercase', fontWeight: 800 }}>
        {label}
      </div>
      <div style={{ color: tone, fontSize: '1.05rem', fontWeight: 850, marginTop: '6px' }}>{value}</div>
    </div>
  );
}

function BlueprintSchematic() {
  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: '8px',
        overflow: 'hidden',
        background: '#03111f',
        aspectRatio: '16 / 9',
        minHeight: '300px',
      }}
    >
      <svg width="100%" height="100%" viewBox="0 0 960 540" role="img" aria-label="Bullet plate target blueprint schematic">
        <defs>
          <pattern id="blueprint-grid" width="28" height="28" patternUnits="userSpaceOnUse">
            <path d="M 28 0 L 0 0 0 28" fill="none" stroke="rgba(125, 211, 252, 0.13)" strokeWidth="1" />
          </pattern>
          <linearGradient id="impact-contour" x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="52%" stopColor="#facc15" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <rect width="960" height="540" fill="#03111f" />
        <rect width="960" height="540" fill="url(#blueprint-grid)" />

        <g stroke="#7dd3fc" strokeWidth="2" fill="none" opacity="0.9">
          <path d="M112 116 C214 172 290 220 365 270" strokeDasharray="10 8" />
          <path d="M350 260 l-32 -4 m32 4 l-16 -28" />
          <text x="96" y="94" fill="#dbeafe" fontSize="20" fontWeight="700">冲击路径</text>
        </g>

        <g filter="url(#glow)">
          <ellipse cx="188" cy="158" rx="42" ry="24" fill="rgba(14, 165, 233, 0.2)" stroke="#bae6fd" strokeWidth="3" />
          <ellipse cx="224" cy="166" rx="20" ry="15" fill="rgba(186, 230, 253, 0.22)" stroke="#bae6fd" strokeWidth="2" />
          <text x="142" y="215" fill="#dbeafe" fontSize="18" fontWeight="700">工程候选体</text>
        </g>

        <g transform="translate(384 112)">
          <rect x="0" y="0" width="300" height="310" rx="10" fill="rgba(8, 47, 73, 0.7)" stroke="#bae6fd" strokeWidth="3" />
          {Array.from({ length: 9 }).map((_, index) => (
            <line key={`v-${index}`} x1={30 + index * 30} y1="0" x2={30 + index * 30} y2="310" stroke="rgba(186, 230, 253, 0.32)" />
          ))}
          {Array.from({ length: 9 }).map((_, index) => (
            <line key={`h-${index}`} x1="0" y1={31 + index * 31} x2="300" y2={31 + index * 31} stroke="rgba(186, 230, 253, 0.32)" />
          ))}
          <ellipse cx="82" cy="156" rx="84" ry="58" fill="url(#impact-contour)" opacity="0.58" />
          <ellipse cx="82" cy="156" rx="38" ry="26" fill="rgba(239, 68, 68, 0.55)" stroke="#fecaca" />
          <path d="M44 134 C88 110 146 128 158 166 C118 204 58 192 44 134Z" fill="none" stroke="#fef08a" strokeWidth="2" />
          <text x="18" y="-18" fill="#dbeafe" fontSize="20" fontWeight="700">靶板网格</text>
          <text x="154" y="294" fill="#fef08a" fontSize="18" fontWeight="700">变形云图</text>
        </g>

        <g stroke="#38bdf8" strokeWidth="3" fill="none">
          <path d="M370 102 h-24 v330 h24" />
          <path d="M700 102 h24 v330 h-24" />
          <path d="M342 138 l24 -18 m-24 62 l24 -18 m-24 62 l24 -18 m-24 62 l24 -18 m-24 62 l24 -18 m-24 62 l24 -18" />
          <path d="M724 138 l-24 -18 m24 62 l-24 -18 m24 62 l-24 -18 m24 62 l-24 -18 m24 62 l-24 -18 m24 62 l-24 -18" />
          <text x="704" y="462" fill="#dbeafe" fontSize="20" fontWeight="700">边界约束</text>
        </g>

        <g transform="translate(742 128)">
          <rect x="0" y="0" width="160" height="214" rx="8" fill="rgba(15, 23, 42, 0.78)" stroke="#7dd3fc" />
          <text x="18" y="32" fill="#dbeafe" fontSize="18" fontWeight="700">验证数据</text>
          <polyline points="18,82 48,62 76,94 108,58 138,74" fill="none" stroke="#22c55e" strokeWidth="3" />
          <polyline points="18,138 48,122 78,132 108,104 138,112" fill="none" stroke="#facc15" strokeWidth="3" />
          <rect x="18" y="162" width="124" height="12" fill="rgba(34, 197, 94, 0.35)" />
          <rect x="18" y="184" width="92" height="12" fill="rgba(245, 158, 11, 0.45)" />
        </g>

        <g>
          <rect x="44" y="438" width="356" height="42" rx="21" fill="rgba(245, 158, 11, 0.1)" stroke="rgba(245, 158, 11, 0.55)" />
          <text x="68" y="465" fill="#facc15" fontSize="18" fontWeight="800">
            Tier 1 工程候选 · not signed validation
          </text>
        </g>
      </svg>
    </div>
  );
}

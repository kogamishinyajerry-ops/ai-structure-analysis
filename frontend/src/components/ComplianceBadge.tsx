import { ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';

interface ComplianceBadgeProps {
  status: 'PASS' | 'FAIL' | 'CRITICAL' | 'N/A';
  standard: string;
}

export function ComplianceBadge({ status, standard }: ComplianceBadgeProps) {
  const getColors = () => {
    switch (status) {
      case 'PASS': return { bg: 'var(--success-glow)', border: 'rgba(74, 138, 94, 0.30)', text: 'var(--success-500)', icon: <ShieldCheck size={14} /> };
      case 'CRITICAL': return { bg: 'rgba(179, 121, 26, 0.10)', border: 'rgba(179, 121, 26, 0.30)', text: 'var(--warn-400)', icon: <ShieldAlert size={14} /> };
      case 'FAIL': return { bg: 'rgba(197, 69, 59, 0.10)', border: 'rgba(197, 69, 59, 0.30)', text: 'var(--danger-400)', icon: <ShieldX size={14} /> };
      default: return { bg: 'var(--c-100)', border: 'var(--border)', text: 'var(--text-muted)', icon: null };
    }
  };

  const colors = getColors();

  return (
    <div style={{ 
      display: 'inline-flex', 
      alignItems: 'center', 
      gap: '6px', 
      padding: '4px 10px', 
      borderRadius: '20px', 
      background: colors.bg, 
      border: `1px solid ${colors.border}`,
      color: colors.text,
      fontSize: '0.75rem',
      fontWeight: 600,
      textTransform: 'uppercase'
    }}>
      {colors.icon}
      {standard}: {status}
    </div>
  );
}

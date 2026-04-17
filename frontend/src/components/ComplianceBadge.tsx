import { ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';

interface ComplianceBadgeProps {
  status: 'PASS' | 'FAIL' | 'CRITICAL' | 'N/A';
  standard: string;
}

export function ComplianceBadge({ status, standard }: ComplianceBadgeProps) {
  const getColors = () => {
    switch (status) {
      case 'PASS': return { bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.2)', text: '#10b981', icon: <ShieldCheck size={14} /> };
      case 'CRITICAL': return { bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.2)', text: '#f59e0b', icon: <ShieldAlert size={14} /> };
      case 'FAIL': return { bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.2)', text: '#ef4444', icon: <ShieldX size={14} /> };
      default: return { bg: 'rgba(148, 163, 184, 0.1)', border: 'rgba(148, 163, 184, 0.2)', text: '#94a3b8', icon: null };
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

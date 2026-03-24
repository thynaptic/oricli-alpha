import { useSCStore } from '../store';

const STATUS_COLORS = {
  connected: '#06D6A0',
  reconnecting: '#FFD166',
  disconnected: '#FF4D6D',
};

export function SovereigntyBadge() {
  const wsStatus = useSCStore(s => s.wsStatus);
  const dot = STATUS_COLORS[wsStatus] ?? STATUS_COLORS.disconnected;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        background: 'rgba(196,164,74,0.08)',
        border: '1px solid rgba(196,164,74,0.2)',
        borderRadius: '20px',
        fontSize: '11px',
        fontFamily: 'var(--font-grotesk)',
        letterSpacing: '0.05em',
        color: 'var(--color-sc-gold)',
        userSelect: 'none',
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot, display: 'inline-block', flexShrink: 0 }} />
      <span>SOVEREIGN</span>
      <span style={{ color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-inter)' }}>
        · No Cloud · No Keys · Local MCI
      </span>
    </div>
  );
}

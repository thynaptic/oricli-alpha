import { useSCStore } from '../store';
import { X } from 'lucide-react';

const SKILLS = [
  'api_designer','benchmark_analyst','data_scientist','devops_sre',
  'digital_guardian','go_engineer','hive_orchestrator','jarvis_ops',
  'knowledge_curator','ml_trainer','offensive_security','prompt_engineer',
  'senior_python_dev','sovereign_planner','system_architect','technical_writer',
];

export function SettingsPanel({ onClose }) {
  const models = useSCStore(s => s.models);
  const activeModel = useSCStore(s => s.activeModel);
  const setActiveModel = useSCStore(s => s.setActiveModel);
  const activeSkill = useSCStore(s => s.activeSkill);
  const setActiveSkill = useSCStore(s => s.setActiveSkill);
  const health = useSCStore(s => s.health);
  const wsStatus = useSCStore(s => s.wsStatus);

  const row = { display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 22 };
  const label = { fontSize: 12, fontWeight: 500, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-inter)' };
  const select = {
    background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border2)',
    color: 'var(--color-sc-text)', borderRadius: 8, padding: '8px 10px',
    fontSize: 13, fontFamily: 'var(--font-inter)', cursor: 'pointer', width: '100%',
  };

  return (
    <>
      {/* Backdrop */}
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 40 }} />
      {/* Panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 340,
        background: 'var(--color-sc-surface)', borderLeft: '1px solid var(--color-sc-border)',
        zIndex: 50, display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 15, color: 'var(--color-sc-text)' }}>Settings</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--color-sc-text-muted)', cursor: 'pointer', display: 'flex', padding: 4 }}>
            <X size={16} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {/* Model */}
          {models.length > 0 && (
            <div style={row}>
              <label style={label}>Model</label>
              <select value={activeModel ?? ''} onChange={e => setActiveModel(e.target.value)} style={select}>
                {models.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
              </select>
            </div>
          )}

          {/* Skill */}
          <div style={row}>
            <label style={label}>Expertise mode</label>
            <select value={activeSkill ?? ''} onChange={e => setActiveSkill(e.target.value || null)} style={select}>
              <option value="">Auto (no specific mode)</option>
              {SKILLS.map(sk => <option key={sk} value={sk}>{sk.replace(/_/g, ' ')}</option>)}
            </select>
            <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
              Activates a specialised profile for this session.
            </span>
          </div>

          {/* Status */}
          <div style={{ ...row, marginTop: 8 }}>
            <label style={label}>System status</label>
            <div style={{
              background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border)',
              borderRadius: 8, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8,
            }}>
              {[
                { label: 'API', value: health?.ok ? 'Connected' : 'Disconnected', ok: health?.ok },
                { label: 'Intelligence stream', value: wsStatus, ok: wsStatus === 'connected' },
                { label: 'API base', value: health?.api_base ?? '—', mono: true },
              ].map(r => (
                <div key={r.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: 'var(--color-sc-text-muted)' }}>{r.label}</span>
                  <span style={{
                    color: r.ok === true ? 'var(--color-sc-success)' : r.ok === false ? 'var(--color-sc-danger)' : 'var(--color-sc-text)',
                    fontFamily: r.mono ? 'var(--font-mono)' : 'var(--font-inter)', fontSize: r.mono ? 11 : 12,
                  }}>{r.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* About */}
          <div style={{ marginTop: 8, padding: '14px', background: 'color-mix(in srgb, var(--color-sc-gold) 5%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 15%, transparent)', borderRadius: 8 }}>
            <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 13, color: 'var(--color-sc-gold)', marginBottom: 6 }}>ORI Studio</div>
            <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)', lineHeight: 1.6 }}>
              Runs entirely on your own infrastructure. No data leaves your server. No third-party model providers. Powered by MCI — Main Central Intelligence.
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

import { useState, useEffect } from 'react';
import type { StatsResponse } from '../types';
import { getStats } from '../utils/api';

const IconFighters = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconEvents = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);

const IconFights = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
  </svg>
);

const IconStats = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
  </svg>
);

export default function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats().then(setStats).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin h-6 w-6 border-2 border-ufc-gold border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!stats) return <div className="text-center py-20 text-ufc-muted">Error cargando estadisticas</div>;

  const dbStats = [
    { label: 'Peleadores', value: stats.database.fighters?.toLocaleString() || '0', icon: <IconFighters /> },
    { label: 'Eventos', value: stats.database.events?.toLocaleString() || '0', icon: <IconEvents /> },
    { label: 'Peleas', value: stats.database.fights?.toLocaleString() || '0', icon: <IconFights /> },
    { label: 'Stats por round', value: stats.database.fight_stats?.toLocaleString() || '0', icon: <IconStats /> },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="mb-10">
        <p className="section-label mb-1.5">Base de datos y modelo</p>
        <h1 className="text-[26px] font-extrabold tracking-tight text-white">
          Estadisticas del sistema
        </h1>
      </div>

      {/* DB Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {dbStats.map(({ label, value, icon }) => (
          <div key={label} className="glass-card p-4 text-center">
            <div className="flex justify-center mb-2 opacity-70">{icon}</div>
            <p className="text-[18px] font-extrabold text-white">{value}</p>
            <p className="text-[10px] text-ufc-muted tracking-[1px] uppercase mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Model Info */}
      <div className="glass-card p-5 mb-4">
        <p className="card-title">Modelo de prediccion</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-ufc-surface rounded-lg p-3">
            <p className="text-ufc-gold text-[16px] font-extrabold">{stats.model_info.features}</p>
            <p className="text-[10px] text-ufc-muted">Features</p>
          </div>
          <div className="bg-ufc-surface rounded-lg p-3">
            <p className="text-ufc-gold text-[16px] font-extrabold">{stats.model_info.models.length}</p>
            <p className="text-[10px] text-ufc-muted">Modelos</p>
          </div>
          <div className="bg-ufc-surface rounded-lg p-3">
            <p className="text-ufc-gold text-[16px] font-extrabold">65.2%</p>
            <p className="text-[10px] text-ufc-muted">Accuracy</p>
          </div>
          <div className="bg-ufc-surface rounded-lg p-3">
            <p className="text-ufc-gold text-[16px] font-extrabold">4 capas</p>
            <p className="text-[10px] text-ufc-muted">Prediccion multinivel</p>
          </div>
        </div>
        <p className="mt-3 text-[11px] text-ufc-muted2">
          {stats.model_info.models.join(' \u2192 ')}
        </p>
      </div>

      {/* Last Event */}
      {stats.last_event && (
        <div className="glass-card p-5 mb-4">
          <p className="card-title">Ultimo evento registrado</p>
          <p className="text-white font-semibold text-[14px]">{stats.last_event.name}</p>
          <p className="text-ufc-muted text-[12px] mt-0.5">{stats.last_event.date_parsed}</p>
        </div>
      )}

      {/* Top Fighters */}
      <div className="glass-card p-5">
        <p className="card-title">Top peleadores por victorias</p>
        <div className="space-y-0">
          {stats.top_fighters_by_wins.map((f, i) => (
            <div key={f.name} className="flex items-center gap-3 py-2.5 border-b border-ufc-border/50 last:border-0">
              <span className="text-ufc-gold font-bold w-5 text-right text-[12px]">{i + 1}</span>
              <span className="flex-1 font-medium text-white text-[13px]">{f.name}</span>
              <span className="text-ufc-muted text-[12px]">{f.wins}-{f.losses}-{f.draws}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
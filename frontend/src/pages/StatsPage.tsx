import { useState, useEffect } from 'react';
import type { StatsResponse } from '../types';
import { getStats } from '../utils/api';

export default function StatsPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats().then(setStats).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin h-8 w-8 border-2 border-ufc-gold border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!stats) return <div className="text-center py-20 text-ufc-muted">Error cargando estadísticas</div>;

  const dbStats = [
    { label: 'Peleadores', value: stats.database.fighters?.toLocaleString() || '0', icon: '🥊' },
    { label: 'Eventos', value: stats.database.events?.toLocaleString() || '0', icon: '📅' },
    { label: 'Peleas', value: stats.database.fights?.toLocaleString() || '0', icon: '⚔️' },
    { label: 'Stats por round', value: stats.database.fight_stats?.toLocaleString() || '0', icon: '📊' },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-black tracking-tight">
          <span className="gold-gradient">Estadísticas</span> del Sistema
        </h1>
        <p className="text-ufc-muted mt-2 text-lg">
          Base de datos y modelo de predicción
        </p>
      </div>

      {/* DB Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {dbStats.map(({ label, value, icon }) => (
          <div key={label} className="glass-card p-5 text-center">
            <div className="text-3xl mb-2 opacity-70">{icon}</div>
            <p className="text-2xl font-black text-white">{value}</p>
            <p className="text-ufc-muted text-sm mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Model Info */}
      <div className="glass-card p-6 mb-6">
        <h2 className="text-lg font-bold mb-4">Modelo de Predicción</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-ufc-dark/50 rounded-lg p-4">
            <p className="text-ufc-gold text-xl font-bold">{stats.model_info.features}</p>
            <p className="text-ufc-muted text-xs">Features</p>
          </div>
          <div className="bg-ufc-dark/50 rounded-lg p-4">
            <p className="text-ufc-gold text-xl font-bold">{stats.model_info.models.length}</p>
            <p className="text-ufc-muted text-xs">Modelos</p>
          </div>
          <div className="bg-ufc-dark/50 rounded-lg p-4">
            <p className="text-ufc-gold text-xl font-bold">60.6%</p>
            <p className="text-ufc-muted text-xs">Accuracy (ganador)</p>
          </div>
          <div className="bg-ufc-dark/50 rounded-lg p-4">
            <p className="text-ufc-gold text-xl font-bold">4 Capas</p>
            <p className="text-ufc-muted text-xs">Predicción multinivel</p>
          </div>
        </div>
        <div className="mt-4 text-sm text-ufc-muted">
          <p>Capas de predicción: {stats.model_info.models.join(' → ')}</p>
        </div>
      </div>

      {/* Last Event */}
      {stats.last_event && (
        <div className="glass-card p-6 mb-6">
          <h2 className="text-lg font-bold mb-3">Último Evento Registrado</h2>
          <p className="text-white">{stats.last_event.name}</p>
          <p className="text-ufc-muted text-sm">{stats.last_event.date_parsed}</p>
        </div>
      )}

      {/* Top Fighters */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-bold mb-4">Top Peleadores por Victorias</h2>
        <div className="space-y-2">
          {stats.top_fighters_by_wins.map((f, i) => (
            <div key={f.name} className="flex items-center gap-3 py-2 border-b border-ufc-border/30 last:border-0">
              <span className="text-ufc-gold font-bold w-6 text-right">{i + 1}</span>
              <span className="flex-1 font-medium text-white">{f.name}</span>
              <span className="text-ufc-muted text-sm">{f.wins}-{f.losses}-{f.draws}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

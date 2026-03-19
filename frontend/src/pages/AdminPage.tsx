import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface DashboardData {
  database: Record<string, number>;
  last_event: { name: string; date_parsed: string; location: string | null } | null;
  recent_events: { name: string; date_parsed: string; location: string | null; total_fights: number }[];
  top_active_fighters: { name: string; wins: number; losses: number; draws: number; weight_lbs: number | null; stance: string | null }[];
  method_distribution: { method_group: string; count: number }[];
  model_info: { features: number; models: string[] };
  fights_by_year: { year: string; count: number }[];
  total_fights_with_result: number;
}

const API_BASE = import.meta.env.PROD
  ? 'https://web-production-2bc52.up.railway.app'
  : '/api';

export default function AdminPage() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }

    fetch(`${API_BASE}/admin/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (r.status === 401 || r.status === 403) {
          logout();
          navigate('/login');
          throw new Error('No autorizado');
        }
        if (!r.ok) throw new Error('Error al cargar dashboard');
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, navigate, logout]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 text-center">
        <div className="animate-spin h-8 w-8 border-2 border-ufc-gold border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-ufc-muted">Cargando dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 text-center">
        <p className="text-ufc-red text-lg">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const methodTotal = data.method_distribution.reduce((s, m) => s + m.count, 0);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-black tracking-tight">
            <span className="gold-gradient">Admin</span> Dashboard
          </h1>
          <p className="text-ufc-muted mt-1">
            Bienvenido, <span className="text-white font-medium">{user?.username}</span>
          </p>
        </div>
        <button onClick={() => { logout(); navigate('/'); }} className="btn-secondary text-sm">
          Cerrar sesión
        </button>
      </div>

      {/* DB Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Peleadores', value: data.database.fighters, icon: '🥊' },
          { label: 'Eventos', value: data.database.events, icon: '🏟️' },
          { label: 'Peleas', value: data.database.fights, icon: '⚔️' },
          { label: 'Stats (filas)', value: data.database.fight_stats, icon: '📊' },
        ].map((s) => (
          <div key={s.label} className="glass-card p-5 text-center">
            <div className="text-2xl mb-2">{s.icon}</div>
            <p className="text-2xl font-black text-white">{s.value.toLocaleString()}</p>
            <p className="text-xs text-ufc-muted mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Model Info + Last Event */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Model Info */}
        <div className="glass-card p-5">
          <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Modelo ML</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-ufc-muted text-sm">Features</span>
              <span className="text-white font-bold">{data.model_info.features}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ufc-muted text-sm">Modelos</span>
              <span className="text-white font-bold">{data.model_info.models.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ufc-muted text-sm">Peleas con resultado</span>
              <span className="text-white font-bold">{data.total_fights_with_result.toLocaleString()}</span>
            </div>
            <div className="mt-3 pt-3 border-t border-ufc-border/50">
              <p className="text-xs text-ufc-muted">Capas de predicción:</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {['Ganador', 'Método', 'Finish/Dec', 'Round'].map((m) => (
                  <span key={m} className="text-xs px-2 py-1 rounded bg-ufc-dark text-ufc-gold border border-ufc-border">
                    {m}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Last Event */}
        <div className="glass-card p-5">
          <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Último evento en BD</h3>
          {data.last_event ? (
            <div>
              <p className="text-lg font-bold text-white">{data.last_event.name}</p>
              <p className="text-ufc-muted text-sm mt-1">{data.last_event.date_parsed}</p>
              {data.last_event.location && (
                <p className="text-ufc-muted text-sm">{data.last_event.location}</p>
              )}
            </div>
          ) : (
            <p className="text-ufc-muted">Sin datos</p>
          )}

          <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mt-6 mb-3">Eventos recientes</h3>
          <div className="space-y-2">
            {data.recent_events.map((e, i) => (
              <div key={i} className="flex items-center justify-between py-1.5 border-b border-ufc-border/30 last:border-0">
                <div>
                  <p className="text-sm text-white">{e.name}</p>
                  <p className="text-xs text-ufc-muted">{e.date_parsed}</p>
                </div>
                <span className="text-xs text-ufc-gold font-bold">{e.total_fights} peleas</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Method Distribution + Fights by Year */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Methods */}
        <div className="glass-card p-5">
          <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Distribución de métodos</h3>
          <div className="space-y-3">
            {data.method_distribution.map((m) => {
              const pct = methodTotal > 0 ? Math.round((m.count / methodTotal) * 100) : 0;
              const colors: Record<string, string> = {
                'KO/TKO': 'bg-ufc-red',
                'Submission': 'bg-purple-500',
                'Decision': 'bg-blue-500',
                'Otro': 'bg-ufc-border',
              };
              return (
                <div key={m.method_group}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-ufc-muted">{m.method_group}</span>
                    <span className="text-white font-bold">{pct}% ({m.count.toLocaleString()})</span>
                  </div>
                  <div className="h-2 bg-ufc-dark rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${colors[m.method_group] || 'bg-ufc-border'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Fights by Year */}
        <div className="glass-card p-5">
          <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Peleas por año</h3>
          <div className="space-y-2">
            {[...data.fights_by_year].reverse().map((f) => {
              const maxCount = Math.max(...data.fights_by_year.map((x) => x.count));
              const pct = maxCount > 0 ? Math.round((f.count / maxCount) * 100) : 0;
              return (
                <div key={f.year} className="flex items-center gap-3">
                  <span className="text-xs text-ufc-muted w-10 text-right">{f.year}</span>
                  <div className="flex-1 h-3 bg-ufc-dark rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-ufc-gold" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-white font-bold w-10">{f.count}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top Fighters */}
      <div className="glass-card p-5">
        <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Top peleadores (por victorias)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ufc-border/50">
                <th className="text-left py-2 px-3 text-ufc-muted font-medium">#</th>
                <th className="text-left py-2 px-3 text-ufc-muted font-medium">Peleador</th>
                <th className="text-center py-2 px-3 text-ufc-muted font-medium">Record</th>
                <th className="text-center py-2 px-3 text-ufc-muted font-medium">Peso</th>
                <th className="text-center py-2 px-3 text-ufc-muted font-medium">Stance</th>
              </tr>
            </thead>
            <tbody>
              {data.top_active_fighters.map((f, i) => (
                <tr key={f.name} className="border-b border-ufc-border/20 hover:bg-ufc-dark/50">
                  <td className="py-2 px-3 text-ufc-muted">{i + 1}</td>
                  <td className="py-2 px-3 text-white font-medium">{f.name}</td>
                  <td className="py-2 px-3 text-center text-ufc-gold font-bold">{f.wins}-{f.losses}-{f.draws}</td>
                  <td className="py-2 px-3 text-center text-ufc-muted">{f.weight_lbs ? `${f.weight_lbs} lbs` : '--'}</td>
                  <td className="py-2 px-3 text-center text-ufc-muted">{f.stance || '--'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

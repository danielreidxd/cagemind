import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

// ── Types ──
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

interface AnalyticsData {
  total_events: number;
  by_type: { event_type: string; count: number }[];
  by_page: { page: string; count: number }[];
  predictions_daily: { day: string; count: number }[];
  top_searched: { detail: string; count: number }[];
  top_predictions: { detail: string; count: number }[];
  by_hour: { hour: number; count: number }[];
}

interface UpdateLog {
  id: number;
  action: string;
  status: string;
  result: string | null;
  started_at: string;
  finished_at: string | null;
}

const API_BASE = import.meta.env.PROD
  ? 'https://web-production-2bc52.up.railway.app'
  : '/api';

type Tab = 'dashboard' | 'analytics' | 'system';

export default function AdminPage() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('dashboard');
  const [dashData, setDashData] = useState<DashboardData | null>(null);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [logs, setLogs] = useState<UpdateLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [updateResult, setUpdateResult] = useState<string | null>(null);

  const authHeaders = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async (t: Tab) => {
    if (!token) { navigate('/login'); return; }
    setLoading(true);
    setError(null);
    try {
      if (t === 'dashboard') {
        const r = await fetch(`${API_BASE}/admin/dashboard`, { headers: authHeaders });
        if (r.status === 401 || r.status === 403) { logout(); navigate('/login'); return; }
        setDashData(await r.json());
      } else if (t === 'analytics') {
        const r = await fetch(`${API_BASE}/admin/analytics`, { headers: authHeaders });
        setAnalyticsData(await r.json());
      } else if (t === 'system') {
        const r = await fetch(`${API_BASE}/admin/update-logs`, { headers: authHeaders });
        const data = await r.json();
        setLogs(data.logs || []);
      }
    } catch (e: any) {
      setError(e.message || 'Error al cargar');
    } finally {
      setLoading(false);
    }
  }, [token, navigate, logout]);

  useEffect(() => { fetchData(tab); }, [tab, fetchData]);

  async function handleUpdate() {
    setUpdating(true);
    setUpdateResult(null);
    try {
      const r = await fetch(`${API_BASE}/admin/update`, {
        method: 'POST',
        headers: authHeaders,
      });
      const data = await r.json();
      setUpdateResult(data.status === 'success'
        ? 'Actualización completada exitosamente'
        : `Error: ${data.output?.slice(0, 200) || 'desconocido'}`);
      // Refresh logs
      fetchData('system');
    } catch (e: any) {
      setUpdateResult(`Error: ${e.message}`);
    } finally {
      setUpdating(false);
    }
  }

  // ── Tab button ──
  const tabBtn = (t: Tab, label: string, icon: string) => (
    <button
      onClick={() => setTab(t)}
      className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
        tab === t ? 'bg-ufc-red text-white' : 'text-ufc-muted hover:text-white hover:bg-ufc-border/50'
      }`}
    >
      <span>{icon}</span> {label}
    </button>
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-black tracking-tight">
            <span className="gold-gradient">Admin</span> Panel
          </h1>
          <p className="text-ufc-muted mt-1">
            Bienvenido, <span className="text-white font-medium">{user?.username}</span>
          </p>
        </div>
        <button onClick={() => { logout(); navigate('/'); }} className="btn-secondary text-sm">
          Cerrar sesión
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {tabBtn('dashboard', 'Dashboard', '📊')}
        {tabBtn('analytics', 'Analytics', '📈')}
        {tabBtn('system', 'Sistema', '⚙️')}
      </div>

      {/* Loading / Error */}
      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin h-8 w-8 border-2 border-ufc-gold border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-ufc-muted">Cargando...</p>
        </div>
      )}
      {error && <div className="glass-card p-4 border-ufc-red border text-ufc-red text-center mb-6">{error}</div>}

      {/* ════════════════ DASHBOARD TAB ════════════════ */}
      {!loading && tab === 'dashboard' && dashData && (
        <div className="space-y-6 animate-fadeIn">
          {/* DB Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Peleadores', value: dashData.database.fighters, icon: '🥊' },
              { label: 'Eventos', value: dashData.database.events, icon: '🏟️' },
              { label: 'Peleas', value: dashData.database.fights, icon: '⚔️' },
              { label: 'Stats', value: dashData.database.fight_stats, icon: '📊' },
            ].map((s) => (
              <div key={s.label} className="glass-card p-5 text-center">
                <div className="text-2xl mb-2">{s.icon}</div>
                <p className="text-2xl font-black text-white">{s.value.toLocaleString()}</p>
                <p className="text-xs text-ufc-muted mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Model + Last Event */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Modelo ML</h3>
              <div className="space-y-3">
                <div className="flex justify-between"><span className="text-ufc-muted text-sm">Features</span><span className="text-white font-bold">{dashData.model_info.features}</span></div>
                <div className="flex justify-between"><span className="text-ufc-muted text-sm">Modelos</span><span className="text-white font-bold">{dashData.model_info.models.length}</span></div>
                <div className="flex justify-between"><span className="text-ufc-muted text-sm">Peleas con resultado</span><span className="text-white font-bold">{dashData.total_fights_with_result.toLocaleString()}</span></div>
                <div className="mt-3 pt-3 border-t border-ufc-border/50">
                  <div className="flex flex-wrap gap-2">
                    {['Ganador', 'Método', 'Finish/Dec', 'Round'].map((m) => (
                      <span key={m} className="text-xs px-2 py-1 rounded bg-ufc-dark text-ufc-gold border border-ufc-border">{m}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Eventos recientes</h3>
              <div className="space-y-2">
                {dashData.recent_events.map((e, i) => (
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

          {/* Methods + Fights by Year */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Métodos de victoria</h3>
              {dashData.method_distribution.map((m) => {
                const total = dashData.method_distribution.reduce((s, x) => s + x.count, 0);
                const pct = total > 0 ? Math.round((m.count / total) * 100) : 0;
                const colors: Record<string, string> = { 'KO/TKO': 'bg-ufc-red', 'Submission': 'bg-purple-500', 'Decision': 'bg-blue-500' };
                return (
                  <div key={m.method_group} className="mb-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-ufc-muted">{m.method_group}</span>
                      <span className="text-white font-bold">{pct}%</span>
                    </div>
                    <div className="h-2 bg-ufc-dark rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${colors[m.method_group] || 'bg-ufc-border'}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Peleas por año</h3>
              {[...dashData.fights_by_year].reverse().map((f) => {
                const max = Math.max(...dashData.fights_by_year.map((x) => x.count));
                return (
                  <div key={f.year} className="flex items-center gap-3 mb-1.5">
                    <span className="text-xs text-ufc-muted w-10 text-right">{f.year}</span>
                    <div className="flex-1 h-3 bg-ufc-dark rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-ufc-gold" style={{ width: `${(f.count / max) * 100}%` }} />
                    </div>
                    <span className="text-xs text-white font-bold w-10">{f.count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════ ANALYTICS TAB ════════════════ */}
      {!loading && tab === 'analytics' && analyticsData && (
        <div className="space-y-6 animate-fadeIn">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="glass-card p-5 text-center">
              <p className="text-2xl font-black text-white">{analyticsData.total_events.toLocaleString()}</p>
              <p className="text-xs text-ufc-muted mt-1">Eventos totales</p>
            </div>
            {analyticsData.by_type.slice(0, 3).map((t) => (
              <div key={t.event_type} className="glass-card p-5 text-center">
                <p className="text-2xl font-black text-white">{t.count.toLocaleString()}</p>
                <p className="text-xs text-ufc-muted mt-1">{t.event_type === 'page_view' ? 'Page views' : t.event_type === 'prediction' ? 'Predicciones' : t.event_type === 'search' ? 'Búsquedas' : t.event_type}</p>
              </div>
            ))}
          </div>

          {/* Page views + Predictions daily */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* By page */}
            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Views por sección</h3>
              {analyticsData.by_page.length > 0 ? analyticsData.by_page.map((p) => {
                const max = Math.max(...analyticsData.by_page.map((x) => x.count));
                const pct = max > 0 ? Math.round((p.count / max) * 100) : 0;
                return (
                  <div key={p.page} className="mb-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-ufc-muted capitalize">{p.page}</span>
                      <span className="text-white font-bold">{p.count}</span>
                    </div>
                    <div className="h-2 bg-ufc-dark rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-ufc-gold" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              }) : <p className="text-ufc-muted text-sm">Sin datos aún</p>}
            </div>

            {/* Predictions daily */}
            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Predicciones por día</h3>
              {analyticsData.predictions_daily.length > 0 ? [...analyticsData.predictions_daily].reverse().map((d) => {
                const max = Math.max(...analyticsData.predictions_daily.map((x) => x.count));
                return (
                  <div key={d.day} className="flex items-center gap-3 mb-1.5">
                    <span className="text-xs text-ufc-muted w-20">{d.day}</span>
                    <div className="flex-1 h-3 bg-ufc-dark rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-ufc-red" style={{ width: `${(d.count / max) * 100}%` }} />
                    </div>
                    <span className="text-xs text-white font-bold w-8">{d.count}</span>
                  </div>
                );
              }) : <p className="text-ufc-muted text-sm">Sin predicciones registradas</p>}
            </div>
          </div>

          {/* Top searched + Top predictions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Peleadores más buscados</h3>
              {analyticsData.top_searched.length > 0 ? (
                <div className="space-y-2">
                  {analyticsData.top_searched.map((s, i) => (
                    <div key={i} className="flex items-center justify-between py-1 border-b border-ufc-border/20 last:border-0">
                      <span className="text-sm text-white">{s.detail}</span>
                      <span className="text-xs text-ufc-gold font-bold">{s.count}</span>
                    </div>
                  ))}
                </div>
              ) : <p className="text-ufc-muted text-sm">Sin búsquedas registradas</p>}
            </div>

            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Predicciones más populares</h3>
              {analyticsData.top_predictions.length > 0 ? (
                <div className="space-y-2">
                  {analyticsData.top_predictions.map((p, i) => (
                    <div key={i} className="flex items-center justify-between py-1 border-b border-ufc-border/20 last:border-0">
                      <span className="text-sm text-white">{p.detail}</span>
                      <span className="text-xs text-ufc-gold font-bold">{p.count}</span>
                    </div>
                  ))}
                </div>
              ) : <p className="text-ufc-muted text-sm">Sin predicciones registradas</p>}
            </div>
          </div>

          {/* Activity by hour */}
          {analyticsData.by_hour.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Actividad por hora (UTC)</h3>
              <div className="flex items-end gap-1 h-24">
                {Array.from({ length: 24 }, (_, h) => {
                  const entry = analyticsData.by_hour.find((x) => x.hour === h);
                  const count = entry?.count || 0;
                  const max = Math.max(...analyticsData.by_hour.map((x) => x.count), 1);
                  return (
                    <div key={h} className="flex-1 flex flex-col items-center gap-1" title={`${h}:00 — ${count} eventos`}>
                      <div className="w-full bg-ufc-gold/80 rounded-t" style={{ height: `${(count / max) * 80}px`, minHeight: count > 0 ? 4 : 0 }} />
                      {h % 4 === 0 && <span className="text-[8px] text-ufc-muted">{h}h</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════════ SYSTEM TAB ════════════════ */}
      {!loading && tab === 'system' && (
        <div className="space-y-6 animate-fadeIn">
          {/* Update button */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Actualizar carteleras</h3>
                <p className="text-ufc-muted text-sm mt-1">
                  Ejecuta el scraper de eventos upcoming de UFCStats.com
                </p>
              </div>
              <button
                onClick={handleUpdate}
                disabled={updating}
                className="btn-primary px-6"
              >
                {updating ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Ejecutando...
                  </span>
                ) : 'Actualizar ahora'}
              </button>
            </div>
            {updateResult && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${
                updateResult.startsWith('Error') ? 'bg-red-500/10 text-red-400 border border-red-500/30' : 'bg-green-500/10 text-green-400 border border-green-500/30'
              }`}>
                {updateResult}
              </div>
            )}
          </div>

          {/* Logs */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs text-ufc-muted font-bold uppercase tracking-wider">Historial de actualizaciones</h3>
              <button onClick={() => fetchData('system')} className="text-xs text-ufc-muted hover:text-white transition-colors">
                Refrescar
              </button>
            </div>

            {logs.length > 0 ? (
              <div className="space-y-2">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-3 py-3 border-b border-ufc-border/30 last:border-0">
                    <div className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${
                      log.status === 'success' ? 'bg-green-500' :
                      log.status === 'running' ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-white font-medium">{log.action}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          log.status === 'success' ? 'bg-green-500/10 text-green-400' :
                          log.status === 'running' ? 'bg-yellow-500/10 text-yellow-400' : 'bg-red-500/10 text-red-400'
                        }`}>
                          {log.status}
                        </span>
                      </div>
                      <p className="text-xs text-ufc-muted mt-0.5">{log.started_at}</p>
                      {log.result && (
                        <pre className="text-xs text-ufc-muted mt-2 bg-ufc-dark p-2 rounded overflow-x-auto max-h-24 whitespace-pre-wrap">
                          {log.result.slice(0, 500)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-ufc-muted text-sm text-center py-6">No hay registros de actualizaciones</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

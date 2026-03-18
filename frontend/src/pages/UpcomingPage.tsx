import { useState, useEffect, useCallback } from 'react';
import FightDetailInline from '../components/FightDetailInline';

interface FightPrediction {
  predicted_winner: string;
  prob_a: number;
  prob_b: number;
  confidence: number;
  method_prediction: Record<string, number>;
  correct: boolean | null;
}

interface EventFight {
  fighter_a: string;
  fighter_b: string;
  winner: string | null;
  method: string | null;
  round: number | null;
  time: string | null;
  weight_class: string | null;
  is_draw: number;
  is_no_contest: number;
  prediction: FightPrediction | null;
}

interface EventData {
  total_events: number;
  page: number;
  total_pages: number;
  event: { event_id: string; name: string; date_parsed: string; location: string | null } | null;
  fights: EventFight[];
  model_accuracy: { correct: number; total: number; percentage: number };
}

export default function UpcomingPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<EventData | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState<'left' | 'right' | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const fetchEvent = useCallback(async (p: number) => {
    setLoading(true);
    setExpandedIdx(null);
    try {
      const res = await fetch('/api/events?page=' + p);
      const json = await res.json();
      setData(json);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchEvent(page); }, [page, fetchEvent]);

  const navigateRef = { page, totalPages: data?.total_pages || 1 };

  function doNavigate(dir: 'prev' | 'next') {
    const newPage = dir === 'prev' ? navigateRef.page - 1 : navigateRef.page + 1;
    if (newPage < 1 || newPage > navigateRef.totalPages) return;
    setTransitioning(dir === 'prev' ? 'right' : 'left');
    setTimeout(() => {
      setPage(newPage);
      setTransitioning(null);
    }, 200);
  }

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'ArrowLeft') doNavigate('prev');
      if (e.key === 'ArrowRight') doNavigate('next');
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  });

  function toggleFight(idx: number) {
    setExpandedIdx(expandedIdx === idx ? null : idx);
  }

  const accuracyColor = (pct: number) => {
    if (pct >= 70) return 'text-green-400';
    if (pct >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <h1 className="text-4xl font-black tracking-tight">
          Peleas <span className="gold-gradient">Oficiales</span>
        </h1>
        <p className="text-ufc-muted mt-2">
          Historial de eventos · Click en una pelea para ver el desglose completo
        </p>
      </div>

      {data && (
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => doNavigate('prev')} disabled={page <= 1}
            className="btn-secondary flex items-center gap-2 disabled:opacity-30">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Reciente
          </button>
          <div className="text-center">
            <span className="text-ufc-muted text-sm">Evento {page} de {data.total_pages}</span>
            <div className="flex items-center gap-1 mt-1 justify-center">
              {Array.from({ length: Math.min(7, data.total_pages) }, (_, i) => {
                const startPage = Math.max(1, Math.min(page - 3, data.total_pages - 6));
                const p = startPage + i;
                return (
                  <button key={p} onClick={() => setPage(p)}
                    className={'w-2 h-2 rounded-full transition-all ' + (p === page ? 'bg-ufc-gold w-6' : 'bg-ufc-border hover:bg-ufc-muted')} />
                );
              })}
            </div>
          </div>
          <button onClick={() => doNavigate('next')} disabled={page >= (data?.total_pages || 1)}
            className="btn-secondary flex items-center gap-2 disabled:opacity-30">
            Antiguo
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}

      {loading && (
        <div className="text-center py-20">
          <div className="animate-spin h-8 w-8 border-2 border-ufc-gold border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-ufc-muted">Analizando evento...</p>
        </div>
      )}

      {!loading && data?.event && (
        <div className={'transition-all duration-200 ' + (
          transitioning === 'left' ? 'translate-x-[-20px] opacity-0' :
          transitioning === 'right' ? 'translate-x-[20px] opacity-0' : 'translate-x-0 opacity-100'
        )}>
          {/* Event Header */}
          <div className="glass-card p-6 mb-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-black text-white">{data.event.name}</h2>
                <p className="text-ufc-muted mt-1">
                  {new Date(data.event.date_parsed).toLocaleDateString('es-MX', {
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                  })}
                  {data.event.location && (' \u00b7 ' + data.event.location)}
                </p>
              </div>
              <div className="text-center bg-ufc-dark/50 rounded-lg px-4 py-2">
                <p className={'text-2xl font-black ' + accuracyColor(data.model_accuracy.percentage)}>
                  {data.model_accuracy.correct}/{data.model_accuracy.total}
                </p>
                <p className="text-ufc-muted text-xs">Modelo ({data.model_accuracy.percentage}%)</p>
              </div>
            </div>
          </div>

          {/* Fights List - Accordion */}
          <div className="space-y-2">
            {data.fights.map((fight, idx) => {
              const pred = fight.prediction;
              const isExpanded = expandedIdx === idx;

              let dotColor = 'bg-ufc-border';
              if (pred && pred.correct === true) dotColor = 'bg-green-500';
              if (pred && pred.correct === false) dotColor = 'bg-red-500';

              const aWon = fight.winner === fight.fighter_a;
              const bWon = fight.winner === fight.fighter_b;

              const methodShort = (m: string | null) => {
                if (!m) return '';
                const u = m.toUpperCase();
                if (u.includes('KO') || u.includes('TKO')) return 'KO/TKO';
                if (u.includes('SUB')) return 'SUB';
                if (u.includes('U-DEC')) return 'UD';
                if (u.includes('S-DEC')) return 'SD';
                if (u.includes('M-DEC')) return 'MD';
                if (u.includes('DEC')) return 'DEC';
                return m.slice(0, 10);
              };

              const hasWinner = fight.winner && !fight.is_draw && !fight.is_no_contest;

              return (
                <div key={idx} className={'glass-card overflow-hidden transition-all duration-200 ' +
                  (isExpanded ? 'border-ufc-gold/40' : 'hover:border-ufc-gold/20')}>
                  {/* Fight Row - Clickable */}
                  <div
                    onClick={() => toggleFight(idx)}
                    className="px-4 py-3 flex items-center gap-3 cursor-pointer select-none"
                  >
                    <div className={'w-2.5 h-2.5 rounded-full flex-shrink-0 ' + dotColor} />
                    <div className="flex-1 text-right">
                      <span className={'text-sm font-medium ' + (aWon ? 'text-white' : 'text-ufc-muted')}>{fight.fighter_a}</span>
                      {pred && <span className="text-xs text-ufc-muted ml-2">{(pred.prob_a * 100).toFixed(0)}%</span>}
                    </div>
                    <div className="flex-shrink-0 text-center w-28">
                      {hasWinner ? (
                        <div>
                          <span className="text-xs font-bold text-ufc-gold">{methodShort(fight.method)}</span>
                          {fight.round && <span className="text-xs text-ufc-muted ml-1">R{fight.round}</span>}
                        </div>
                      ) : fight.is_draw ? (
                        <span className="text-xs text-yellow-400 font-medium">DRAW</span>
                      ) : fight.is_no_contest ? (
                        <span className="text-xs text-ufc-muted font-medium">NC</span>
                      ) : (
                        <span className="text-xs text-ufc-muted">vs</span>
                      )}
                      {fight.weight_class && <p className="text-[10px] text-ufc-muted/60 mt-0.5">{fight.weight_class}</p>}
                    </div>
                    <div className="flex-1 text-left">
                      {pred && <span className="text-xs text-ufc-muted mr-2">{(pred.prob_b * 100).toFixed(0)}%</span>}
                      <span className={'text-sm font-medium ' + (bWon ? 'text-white' : 'text-ufc-muted')}>{fight.fighter_b}</span>
                    </div>
                    <div className="flex-shrink-0 w-16 text-right flex items-center justify-end gap-2">
                      {pred ? (
                        <span className={'text-xs font-bold ' + (pred.correct ? 'text-green-400' : 'text-red-400')}>
                          {pred.correct ? 'OK' : 'MISS'}
                        </span>
                      ) : <span className="text-xs text-ufc-muted/40">--</span>}
                      <svg className={'w-3.5 h-3.5 text-ufc-muted transition-transform duration-200 ' + (isExpanded ? 'rotate-180' : '')}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>

                  {/* Expanded Detail */}
                  {isExpanded && (
                    <div className="px-4 pb-4 border-t border-ufc-border/50">
                      <FightDetailInline
                        fighterA={fight.fighter_a}
                        fighterB={fight.fighter_b}
                        realWinner={fight.winner}
                        realMethod={fight.method}
                        realRound={fight.round}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 mt-6 text-xs text-ufc-muted">
            <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-green-500" /><span>Correcta</span></div>
            <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-red-500" /><span>Incorrecta</span></div>
            <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-ufc-border" /><span>Sin datos</span></div>
          </div>

          <div className="text-center mt-6 text-ufc-muted/50 text-xs">
            Flechas \u2190 \u2192 para cambiar evento &middot; Click en una pelea para expandir
          </div>
        </div>
      )}

      {!loading && !data?.event && (
        <div className="text-center py-20 text-ufc-muted">No se encontraron eventos.</div>
      )}

      {data && data.total_pages > 10 && (
        <div className="flex items-center justify-center gap-3 mt-6">
          <span className="text-ufc-muted text-sm">Ir al evento:</span>
          <input type="number" min={1} max={data.total_pages} value={page}
            onChange={(e) => { const v = parseInt(e.target.value); if (v >= 1 && v <= data.total_pages) setPage(v); }}
            className="w-20 bg-ufc-dark border border-ufc-border rounded px-3 py-1 text-center text-sm text-white focus:outline-none focus:border-ufc-gold" />
          <span className="text-ufc-muted text-sm">/ {data.total_pages}</span>
        </div>
      )}
    </div>
  );
}

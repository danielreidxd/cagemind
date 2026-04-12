import { useState, useEffect, useCallback } from 'react';
import FightDetailInline from '../components/FightDetailInline';
import EventCardGenerator from '../components/EventCardGenerator';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE } from '../config';

interface UpcomingFight {
  fighter_a: string;
  fighter_b: string;
  weight_class: string | null;
  prediction: {
    predicted_winner: string;
    prob_a: number;
    prob_b: number;
    confidence: string;
    confidence_score?: number;
    method_prediction: Record<string, number>;
  } | null;
  odds?: {
    bookmaker: string;
    odds_a: number;
    odds_b: number;
    implied_a: number;
    implied_b: number;
  } | null;
  value_bet?: {
    fighter: string;
    value_pct: number;
    american_odds: number;
    bookmaker: string;
  } | null;
}

interface UpcomingEvent {
  name: string;
  date: string;
  location: string | null;
  fights: UpcomingFight[];
  total_fights: number;
  predicted_fights: number;
}


export default function NextEventsPage() {
  const [events, setEvents] = useState<UpcomingEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [transitioning, setTransitioning] = useState<'left' | 'right' | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const { user, token } = useAuth();

  // Picks state: { "fighterA|fighterB": "pickedWinner" }
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [pickLoading, setPickLoading] = useState<string | null>(null);

  useEffect(() => {
    fetch(API_BASE + '/upcoming')
      .then(r => r.json())
      .then(data => {
        if (data.events) {
          const now = new Date();
          const futureEvents = data.events.filter((e: UpcomingEvent) => {
            if (!e.date) return true;
            try {
              return new Date(e.date) >= now;
            } catch {
              return true;
            }
          });
          setEvents(futureEvents);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const totalPages = events.length;
  const currentEvent = events[page - 1] || null;

  // Load picks when event changes and user is logged in
  useEffect(() => {
    if (!currentEvent || !token) {
      setPicks({});
      return;
    }
    fetch(`${API_BASE}/picks/${encodeURIComponent(currentEvent.name)}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : { picks: [] })
      .then(data => {
        const map: Record<string, string> = {};
        for (const p of data.picks || []) {
          map[`${p.fighter_a}|${p.fighter_b}`] = p.picked_winner;
        }
        setPicks(map);
      })
      .catch(() => setPicks({}));
  }, [currentEvent?.name, token]);

  const submitPick = useCallback(async (fight: UpcomingFight, pickedWinner: string) => {
    if (!token || !currentEvent) return;
    const key = `${fight.fighter_a}|${fight.fighter_b}`;
    setPickLoading(key);
    try {
      const res = await fetch(`${API_BASE}/picks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          event_name: currentEvent.name,
          fighter_a: fight.fighter_a,
          fighter_b: fight.fighter_b,
          picked_winner: pickedWinner,
        }),
      });
      if (res.ok) {
        setPicks(prev => ({ ...prev, [key]: pickedWinner }));
      }
    } catch { }
    setPickLoading(null);
  }, [token, currentEvent]);

  function doNavigate(dir: 'prev' | 'next') {
    const newPage = dir === 'prev' ? page - 1 : page + 1;
    if (newPage < 1 || newPage > totalPages) return;
    setTransitioning(dir === 'prev' ? 'right' : 'left');
    setExpandedIdx(null);
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

  function daysUntil(dateStr: string) {
    try {
      const diff = Math.ceil((new Date(dateStr).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
      if (diff === 0) return 'Hoy';
      if (diff === 1) return 'Manana';
      if (diff < 0) return 'Pasado';
      return 'En ' + diff + ' dias';
    } catch {
      return '';
    }
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8 text-center">
        <div className="animate-spin h-8 w-8 border-2 border-ufc-gold border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-ufc-muted">Cargando eventos proximos...</p>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-black tracking-tight"><span className="gold-gradient">Proximamente</span></h1>
        </div>
        <div className="glass-card p-10 text-center">
          <p className="text-xl text-white mb-3">No hay eventos proximos</p>
          <p className="text-ufc-muted">Ejecuta el scraper para obtener las carteleras:</p>
          <code className="block mt-3 bg-ufc-dark px-4 py-2 rounded text-ufc-gold text-sm">python scrape_upcoming.py</code>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <h1 className="text-4xl font-black tracking-tight">
          <span className="gold-gradient">Proximamente</span>
        </h1>
        <p className="text-ufc-muted mt-2">
          Predicciones para los proximos {totalPages} eventos UFC
        </p>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mb-6 gap-2">
        <button onClick={() => doNavigate('prev')} disabled={page <= 1}
          className="btn-secondary flex items-center gap-1 px-3 py-2 text-sm disabled:opacity-30">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="hidden sm:inline">Anterior</span>
        </button>
        <div className="text-center min-w-0">
          <span className="text-ufc-muted text-sm">{page} de {totalPages}</span>
          <div className="flex items-center gap-1 mt-1 justify-center overflow-hidden">
            {events.map((_, i) => (
              <button key={i} onClick={() => { setExpandedIdx(null); setPage(i + 1); }}
                className={'w-2 h-2 rounded-full transition-all flex-shrink-0 ' +
                  (i + 1 === page ? 'bg-ufc-gold w-4' : 'bg-ufc-border hover:bg-ufc-muted')} />
            ))}
          </div>
        </div>
        <button onClick={() => doNavigate('next')} disabled={page >= totalPages}
          className="btn-secondary flex items-center gap-1 px-3 py-2 text-sm disabled:opacity-30">
          <span className="hidden sm:inline">Siguiente</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Event Card */}
      {currentEvent && (
        <div className={'transition-all duration-200 ' + (
          transitioning === 'left' ? 'translate-x-[-20px] opacity-0' :
            transitioning === 'right' ? 'translate-x-[20px] opacity-0' : 'translate-x-0 opacity-100'
        )}>
          {/* Event Header */}
          <div className="glass-card p-6 mb-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-black text-white">{currentEvent.name}</h2>
                <p className="text-ufc-muted mt-1">
                  {currentEvent.date}
                  {currentEvent.location && (' \u00b7 ' + currentEvent.location)}
                </p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span className="text-ufc-gold text-lg font-bold bg-ufc-dark/50 px-4 py-2 rounded-lg inline-block">
                  {daysUntil(currentEvent.date)}
                </span>
                <p className="text-ufc-muted text-xs">
                  {currentEvent.total_fights} peleas &middot; {currentEvent.predicted_fights} predicciones
                </p>
                <EventCardGenerator
                  eventName={currentEvent.name}
                  eventDate={currentEvent.date}
                  location={currentEvent.location}
                  fights={currentEvent.fights}
                  totalFights={currentEvent.total_fights}
                  predictedFights={currentEvent.predicted_fights}
                />
              </div>
            </div>
          </div>

          {/* Fights List */}
          <div className="space-y-2">
            {currentEvent.fights.map((fight, idx) => {
              const pred = fight.prediction;
              const isExpanded = expandedIdx === idx;
              const fightKey = `${fight.fighter_a}|${fight.fighter_b}`;
              const myPick = picks[fightKey];
              const isSubmitting = pickLoading === fightKey;

              let pctA = pred ? Math.round(pred.prob_a * 100) : 0;
              let pctB = pred ? 100 - pctA : 0;

              if (pred && pctA === 50 && pctB === 50) {
                if (pred.prob_a > pred.prob_b) {
                  pctA = 51; pctB = 49;
                } else {
                  pctA = 49; pctB = 51;
                }
              }

              return (
                <div key={idx} className={'glass-card overflow-hidden transition-all duration-200 ' +
                  (isExpanded ? 'border-ufc-gold/40' : pred ? 'hover:border-ufc-gold/20' : 'opacity-60')}>
                  {/* Fight Row */}
                  <div
                    onClick={() => pred && toggleFight(idx)}
                    className={'px-4 py-3 flex items-center gap-3 select-none ' +
                      (pred ? 'cursor-pointer' : '')}
                  >
                    {fight.value_bet ? (
                      <span className="text-[8px] font-black bg-green-500/20 text-green-400 border border-green-500/30 px-1.5 py-0.5 rounded flex-shrink-0 leading-tight">
                        VALUE
                      </span>
                    ) : (
                      <div className={'w-2.5 h-2.5 rounded-full flex-shrink-0 ' +
                        (pred ? 'bg-ufc-gold' : 'bg-ufc-border')} />
                    )}

                    <div className="flex-1 text-right">
                      <span className={'text-sm font-medium ' +
                        (pred && pred.predicted_winner === fight.fighter_a ? 'text-white' : 'text-ufc-muted')}>
                        {fight.fighter_a}
                      </span>
                      {pred && (
                        <span className={'text-xs ml-2 font-bold ' +
                          (pred.prob_a > pred.prob_b ? 'text-ufc-gold' : 'text-ufc-muted')}>
                          {pctA}%
                        </span>
                      )}
                    </div>

                    <div className="flex-shrink-0 text-center w-28">
                      <span className="text-xs text-ufc-muted font-medium">vs</span>
                      {fight.weight_class && (
                        <p className="text-[10px] text-ufc-muted/50 mt-0.5">{fight.weight_class}</p>
                      )}
                      {pred && pred.confidence && typeof pred.confidence === 'string' && pred.confidence !== 'HIGH' && (
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full mt-0.5 inline-block ${pred.confidence === 'LOW' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                          }`}>
                          {pred.confidence}
                        </span>
                      )}
                    </div>

                    <div className="flex-1 text-left">
                      {pred && (
                        <span className={'text-xs mr-2 font-bold ' +
                          (pred.prob_b > pred.prob_a ? 'text-ufc-gold' : 'text-ufc-muted')}>
                          {pctB}%
                        </span>
                      )}
                      <span className={'text-sm font-medium ' +
                        (pred && pred.predicted_winner === fight.fighter_b ? 'text-white' : 'text-ufc-muted')}>
                        {fight.fighter_b}
                      </span>
                    </div>

                    <div className="flex-shrink-0 w-8 text-right">
                      {pred ? (
                        <svg className={'w-3.5 h-3.5 text-ufc-muted transition-transform duration-200 inline ' +
                          (isExpanded ? 'rotate-180' : '')}
                          fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      ) : (
                        <span className="text-[10px] text-ufc-muted/40">N/A</span>
                      )}
                    </div>
                  </div>

                  {/* Pick Row */}
                  {pred && (
                    <div className="px-4 pb-2 flex items-center gap-2 justify-center">
                      {user ? (
                        <>
                          <span className="text-[10px] text-ufc-muted mr-1">Tu pick:</span>
                          <button
                            onClick={(e) => { e.stopPropagation(); submitPick(fight, fight.fighter_a); }}
                            disabled={isSubmitting}
                            className={`text-xs px-3 py-1 rounded-full font-medium transition-all ${myPick === fight.fighter_a
                              ? 'bg-ufc-red text-white'
                              : 'bg-ufc-dark text-ufc-muted hover:text-white hover:bg-ufc-red/30 border border-ufc-border'
                              }`}
                          >
                            {fight.fighter_a}
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); submitPick(fight, fight.fighter_b); }}
                            disabled={isSubmitting}
                            className={`text-xs px-3 py-1 rounded-full font-medium transition-all ${myPick === fight.fighter_b
                              ? 'bg-blue-500 text-white'
                              : 'bg-ufc-dark text-ufc-muted hover:text-white hover:bg-blue-500/30 border border-ufc-border'
                              }`}
                          >
                            {fight.fighter_b}
                          </button>
                        </>
                      ) : (
                        <a href="/register" className="text-[10px] text-ufc-gold hover:underline">
                          Regístrate para hacer tus picks
                        </a>
                      )}
                    </div>
                  )}

                  {/* Expanded Detail */}
                  {isExpanded && pred && (
                    <div className="px-4 pb-4 border-t border-ufc-border/50">
                      <FightDetailInline
                        fighterA={fight.fighter_a}
                        fighterB={fight.fighter_b}
                        realWinner={null}
                        realMethod={null}
                        realRound={null}
                        eventName={currentEvent?.name}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center justify-center gap-6 mt-6 text-xs text-ufc-muted">
            <div className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-ufc-gold" />
              <span>Con prediccion</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[8px] font-black bg-green-500/20 text-green-400 border border-green-500/30 px-1 py-0.5 rounded leading-tight">VALUE</span>
              <span>Value bet detectado</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-ufc-border" />
              <span>Peleador no encontrado</span>
            </div>
          </div>

          <div className="text-center mt-6 text-ufc-muted/50 text-xs">
            Flechas ← → para navegar · Click en una pelea para ver prediccion completa
          </div>
        </div>
      )}
    </div>
  );
}
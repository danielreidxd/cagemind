import { useState, useEffect, useCallback } from 'react';
import FightDetailInline from '../components/FightDetailInline';

interface UpcomingFight {
  fighter_a: string;
  fighter_b: string;
  weight_class: string | null;
  prediction: {
    predicted_winner: string;
    prob_a: number;
    prob_b: number;
    confidence: number;
    method_prediction: Record<string, number>;
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

  useEffect(() => {
    const API_BASE = import.meta.env.PROD ? 'https://web-production-2bc52.up.railway.app' : '/api';
    fetch(API_BASE + '/upcoming')
      .then(r => r.json())
      .then(data => {
        if (data.events) {
          // Filtrar solo eventos futuros y ordenar por fecha ascendente (más próximo primero)
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
              <div className="text-center">
                <span className="text-ufc-gold text-lg font-bold bg-ufc-dark/50 px-4 py-2 rounded-lg inline-block">
                  {daysUntil(currentEvent.date)}
                </span>
                <p className="text-ufc-muted text-xs mt-2">
                  {currentEvent.total_fights} peleas &middot; {currentEvent.predicted_fights} predicciones
                </p>
              </div>
            </div>
          </div>

          {/* Fights List - Accordion */}
          <div className="space-y-2">
            {currentEvent.fights.map((fight, idx) => {
              const pred = fight.prediction;
              const isExpanded = expandedIdx === idx;

              return (
                <div key={idx} className={'glass-card overflow-hidden transition-all duration-200 ' +
                  (isExpanded ? 'border-ufc-gold/40' : pred ? 'hover:border-ufc-gold/20' : 'opacity-60')}>
                  {/* Fight Row */}
                  <div
                    onClick={() => pred && toggleFight(idx)}
                    className={'px-4 py-3 flex items-center gap-3 select-none ' +
                      (pred ? 'cursor-pointer' : '')}
                  >
                    <div className={'w-2.5 h-2.5 rounded-full flex-shrink-0 ' +
                      (pred ? 'bg-ufc-gold' : 'bg-ufc-border')} />

                    <div className="flex-1 text-right">
                      <span className={'text-sm font-medium ' +
                        (pred && pred.predicted_winner === fight.fighter_a ? 'text-white' : 'text-ufc-muted')}>
                        {fight.fighter_a}
                      </span>
                      {pred && (
                        <span className={'text-xs ml-2 font-bold ' +
                          (pred.prob_a > pred.prob_b ? 'text-ufc-gold' : 'text-ufc-muted')}>
                          {(pred.prob_a * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>

                    <div className="flex-shrink-0 text-center w-28">
                      <span className="text-xs text-ufc-muted font-medium">vs</span>
                      {fight.weight_class && (
                        <p className="text-[10px] text-ufc-muted/50 mt-0.5">{fight.weight_class}</p>
                      )}
                    </div>

                    <div className="flex-1 text-left">
                      {pred && (
                        <span className={'text-xs mr-2 font-bold ' +
                          (pred.prob_b > pred.prob_a ? 'text-ufc-gold' : 'text-ufc-muted')}>
                          {(pred.prob_b * 100).toFixed(0)}%
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
              <div className="w-2.5 h-2.5 rounded-full bg-ufc-border" />
              <span>Peleador no encontrado</span>
            </div>
          </div>

          <div className="text-center mt-6 text-ufc-muted/50 text-xs">
            Flechas \u2190 \u2192 para navegar &middot; Click en una pelea para ver prediccion completa
          </div>
        </div>
      )}
    </div>
  );
}

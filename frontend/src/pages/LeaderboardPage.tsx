import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.PROD
  ? 'https://web-production-2bc52.up.railway.app'
  : '/api';

interface LeaderboardEntry {
  username: string;
  correct: number;
  total: number;
  accuracy: number;
}

interface LeaderboardData {
  leaderboard: LeaderboardEntry[];
  cagemind: { correct: number; total: number; accuracy: number };
}

export default function LeaderboardPage() {
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/leaderboard`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 text-center">
        <div className="animate-spin h-6 w-6 border-2 border-ufc-gold border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-ufc-muted text-[13px]">Cargando ranking...</p>
      </div>
    );
  }

  const hasData = data && (data.leaderboard.length > 0 || data.cagemind.total > 0);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <p className="section-label mb-1.5">Competencia</p>
        <h1 className="text-[26px] font-extrabold tracking-tight text-white">
          Ranking
        </h1>
        <p className="text-ufc-muted text-[13px] mt-1">
          Puedes superar a CageMind?
        </p>
      </div>

      {!hasData ? (
        <div className="glass-card p-10 text-center">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#525252" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="mx-auto mb-4 opacity-40">
            <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
          </svg>
          <p className="text-[16px] text-white mb-2">Sin datos todavia</p>
          <p className="text-ufc-muted text-[13px]">
            Haz tus picks en Proximamente y cuando se completen los eventos veras los resultados aqui
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* CageMind card */}
          {data && data.cagemind.total > 0 && (
            <div className="glass-card p-4" style={{ borderColor: '#C9A227', borderWidth: '1.5px' }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-ufc-gold/10 flex items-center justify-center">
                    <svg width="16" height="16" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                      <polygon points="50,5 93,27.5 93,72.5 50,95 7,72.5 7,27.5" fill="none" stroke="#C9A227" strokeWidth="6"/>
                      <circle cx="50" cy="50" r="8" fill="#C9A227"/>
                    </svg>
                  </div>
                  <div>
                    <p className="font-bold text-[14px]">
                      <span className="text-ufc-red-light">CAGE</span><span className="text-ufc-gold">MIND</span>
                    </p>
                    <p className="text-[10px] text-ufc-muted">Modelo ML</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[20px] font-extrabold text-ufc-gold">{data.cagemind.accuracy}%</p>
                  <p className="text-[11px] text-ufc-muted">{data.cagemind.correct}/{data.cagemind.total} correctas</p>
                </div>
              </div>
            </div>
          )}

          {/* Users */}
          {data && data.leaderboard.map((entry, i) => {
            const beatsModel = data.cagemind.total > 0 && entry.accuracy > data.cagemind.accuracy;
            return (
              <div key={entry.username} className={`glass-card p-4 ${beatsModel ? 'border-green-800/30' : ''}`} style={beatsModel ? { borderWidth: '1.5px' } : {}}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-ufc-border flex items-center justify-center">
                      <span className={`font-bold ${i < 3 ? 'text-ufc-gold text-[13px]' : 'text-ufc-muted text-[12px]'}`}>{i + 1}</span>
                    </div>
                    <div>
                      <p className="text-white font-semibold text-[14px]">{entry.username}</p>
                      <p className="text-[10px] text-ufc-muted">{entry.total} picks</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-[18px] font-extrabold ${beatsModel ? 'text-green-500' : 'text-white'}`}>{entry.accuracy}%</p>
                    <p className="text-[11px] text-ufc-muted">{entry.correct}/{entry.total}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
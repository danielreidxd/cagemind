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
        <div className="animate-spin h-8 w-8 border-2 border-ufc-gold border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-ufc-muted">Cargando leaderboard...</p>
      </div>
    );
  }

  const hasData = data && (data.leaderboard.length > 0 || data.cagemind.total > 0);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-black tracking-tight">
          <span className="gold-gradient">Leaderboard</span>
        </h1>
        <p className="text-ufc-muted mt-2 text-lg">
          ¿Puedes superar a CageMind?
        </p>
      </div>

      {!hasData ? (
        <div className="glass-card p-10 text-center">
          <div className="text-5xl mb-4 opacity-20">🏆</div>
          <p className="text-xl text-white mb-3">Sin datos todavía</p>
          <p className="text-ufc-muted">
            Haz tus picks en la sección Próximamente y cuando se completen los eventos verás los resultados aquí
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* CageMind card */}
          {data && data.cagemind.total > 0 && (
            <div className="glass-card p-5 border-ufc-gold/40 border-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-ufc-gold/20 flex items-center justify-center">
                    <span className="text-lg">🤖</span>
                  </div>
                  <div>
                    <p className="text-white font-bold text-lg">
                      <span className="text-ufc-red">CAGE</span><span className="text-ufc-gold">MIND</span>
                    </p>
                    <p className="text-xs text-ufc-muted">Modelo ML</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-black text-ufc-gold">{data.cagemind.accuracy}%</p>
                  <p className="text-xs text-ufc-muted">{data.cagemind.correct}/{data.cagemind.total} correctas</p>
                </div>
              </div>
            </div>
          )}

          {/* Users */}
          {data && data.leaderboard.map((entry, i) => {
            const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`;
            const beatsModel = data.cagemind.total > 0 && entry.accuracy > data.cagemind.accuracy;
            return (
              <div key={entry.username} className={`glass-card p-4 ${beatsModel ? 'border-green-500/30 border' : ''}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-ufc-border flex items-center justify-center">
                      <span className={i < 3 ? 'text-lg' : 'text-sm text-ufc-muted font-bold'}>{medal}</span>
                    </div>
                    <div>
                      <p className="text-white font-bold">{entry.username}</p>
                      <p className="text-xs text-ufc-muted">{entry.total} picks</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-xl font-black ${beatsModel ? 'text-green-400' : 'text-white'}`}>{entry.accuracy}%</p>
                    <p className="text-xs text-ufc-muted">{entry.correct}/{entry.total}</p>
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

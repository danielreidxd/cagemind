import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, PieChart, Pie, Tooltip } from 'recharts';
import type { PredictionResponse } from '../types';
import { predictFight, formatHeight, formatProbability } from '../utils/api';
import CardGenerator from './CardGenerator';

interface Props {
  fighterA: string;
  fighterB: string;
  realWinner: string | null;
  realMethod: string | null;
  realRound: number | null;
  eventName?: string;
}

export default function FightDetailInline({ fighterA, fighterB, realWinner, realMethod, realRound, eventName }: Props) {
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await predictFight(fighterA, fighterB);
        if (!cancelled) setPrediction(result);
      } catch (e: any) {
        if (!cancelled) setError(e.message || 'Error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [fighterA, fighterB]);

  if (loading) {
    return (
      <div className="py-6 text-center">
        <div className="animate-spin h-6 w-6 border-2 border-ufc-gold border-t-transparent rounded-full mx-auto mb-2" />
        <p className="text-ufc-muted text-sm">Analizando pelea...</p>
      </div>
    );
  }

  if (error || !prediction) {
    return (
      <div className="py-4 text-center">
        <p className="text-red-400 text-sm">{error || 'No se pudo generar prediccion'}</p>
      </div>
    );
  }

  const { fighter_a_profile: a, fighter_b_profile: b, winner } = prediction;
  const aIsWinner = winner === prediction.fighter_a;
  const predictionCorrect = realWinner ? winner === realWinner : null;

  const methodData = Object.entries(prediction.method_prediction).map(([name, value]) => ({
    name, value: Math.round(value * 100),
  }));

  const roundData = Object.entries(prediction.round_prediction).map(([name, value]) => ({
    name: name.replace('Round ', 'R'), value: Math.round(value * 100),
  }));

  const methodColors: Record<string, string> = {
    'KO/TKO': '#C8102E', 'Submission': '#7F77DD', 'Decision': '#378ADD',
  };

  const methodShort = (m: string | null) => {
    if (!m) return '';
    const u = m.toUpperCase();
    if (u.includes('KO') || u.includes('TKO')) return 'KO/TKO';
    if (u.includes('SUB')) return 'Submission';
    if (u.includes('U-DEC')) return 'Decision Unanime';
    if (u.includes('S-DEC')) return 'Decision Split';
    if (u.includes('M-DEC')) return 'Decision Majority';
    if (u.includes('DEC')) return 'Decision';
    return m;
  };

  return (
    <div className="pt-4 pb-2 space-y-4 animate-fadeIn">
      {/* Real result vs prediction banner */}
      {realWinner && (
        <div className={'rounded-lg p-3 flex items-center justify-between ' +
          (predictionCorrect ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30')}>
          <div>
            <p className="text-xs text-ufc-muted">Resultado real</p>
            <p className="text-sm font-bold text-white">
              {realWinner}
              <span className="text-ufc-gold ml-2 font-normal">
                {methodShort(realMethod)}{realRound ? ' R' + realRound : ''}
              </span>
            </p>
          </div>
          <span className={'text-xs font-bold px-3 py-1 rounded-full ' +
            (predictionCorrect ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400')}>
            {predictionCorrect ? 'Modelo acerto' : 'Modelo fallo'}
          </span>
        </div>
      )}

      {/* Winner prediction */}
      <div className="text-center relative">
        <div className="absolute top-0 right-0">
          <CardGenerator prediction={prediction} eventName={eventName} />
        </div>
        <p className="text-xs text-ufc-muted">Prediccion del modelo</p>
        <p className="text-lg font-black text-white">{winner}</p>
        <p className="text-ufc-gold text-xl font-bold">{formatProbability(prediction.winner_probability)}</p>
      </div>

      {/* Probability bar */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-ufc-red w-12 text-right">{formatProbability(a.win_probability)}</span>
        <div className="flex-1 h-3 bg-ufc-dark rounded-full overflow-hidden flex">
          <div className="h-full bg-ufc-red transition-all duration-500" style={{ width: (a.win_probability * 100) + '%' }} />
          <div className="h-full bg-blue-500 transition-all duration-500" style={{ width: (b.win_probability * 100) + '%' }} />
        </div>
        <span className="text-xs font-bold text-blue-400 w-12">{formatProbability(b.win_probability)}</span>
      </div>

      {/* Fighter comparison side by side compact */}
      <div className="grid grid-cols-2 gap-3">
        <div className={'rounded-lg p-3 text-center ' + (aIsWinner ? 'bg-ufc-red/10 border border-ufc-red/30' : 'bg-ufc-dark/50')}>
          <p className="text-xs text-ufc-red font-bold uppercase">Peleador A</p>
          <p className={'text-sm font-bold mt-1 ' + (aIsWinner ? 'text-white' : 'text-ufc-muted')}>{a.name}</p>
          <p className="text-xs text-ufc-muted">{a.record}</p>
          <div className="mt-2 text-xs text-ufc-muted space-y-0.5">
            <p>{formatHeight(a.height)} · {a.reach ? a.reach + '"' : '--'} reach</p>
            <p>{a.weight ? a.weight + ' lbs' : '--'} · {a.stance || '--'}</p>
          </div>
        </div>
        <div className={'rounded-lg p-3 text-center ' + (!aIsWinner ? 'bg-blue-500/10 border border-blue-500/30' : 'bg-ufc-dark/50')}>
          <p className="text-xs text-blue-400 font-bold uppercase">Peleador B</p>
          <p className={'text-sm font-bold mt-1 ' + (!aIsWinner ? 'text-white' : 'text-ufc-muted')}>{b.name}</p>
          <p className="text-xs text-ufc-muted">{b.record}</p>
          <div className="mt-2 text-xs text-ufc-muted space-y-0.5">
            <p>{formatHeight(b.height)} · {b.reach ? b.reach + '"' : '--'} reach</p>
            <p>{b.weight ? b.weight + ' lbs' : '--'} · {b.stance || '--'}</p>
          </div>
        </div>
      </div>

      {/* Method + Decision charts side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-ufc-dark/50 rounded-lg p-3">
          <p className="text-xs text-ufc-muted font-bold uppercase mb-2">Metodo</p>
          <ResponsiveContainer width="100%" height={100}>
            <BarChart data={methodData} layout="vertical" margin={{ left: 0, right: 10 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#8888AA', fontSize: 10 }} tickFormatter={(v) => v + '%'} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#E0E0E0', fontSize: 10 }} width={65} />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                {methodData.map((entry) => (
                  <Cell key={entry.name} fill={methodColors[entry.name] || '#888'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-ufc-dark/50 rounded-lg p-3">
          <p className="text-xs text-ufc-muted font-bold uppercase mb-2">Decision vs Finish</p>
          <div className="flex items-center gap-3">
            <ResponsiveContainer width="55%" height={90}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'Finish', value: Math.round(prediction.goes_to_decision.finish * 100) },
                    { name: 'Decision', value: Math.round(prediction.goes_to_decision.decision * 100) },
                  ]}
                  cx="50%" cy="50%" innerRadius={25} outerRadius={40} dataKey="value" strokeWidth={0}
                >
                  <Cell fill="#C8102E" />
                  <Cell fill="#378ADD" />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-ufc-red" />
                <span className="text-ufc-muted">Finish <strong className="text-white">{Math.round(prediction.goes_to_decision.finish * 100)}%</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="text-ufc-muted">Dec <strong className="text-white">{Math.round(prediction.goes_to_decision.decision * 100)}%</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Round prediction */}
      {prediction.goes_to_decision.finish > 0.35 && (
        <div className="bg-ufc-dark/50 rounded-lg p-3">
          <p className="text-xs text-ufc-muted font-bold uppercase mb-2">Round de finalizacion</p>
          <ResponsiveContainer width="100%" height={80}>
            <BarChart data={roundData} margin={{ left: 0, right: 0 }}>
              <XAxis dataKey="name" tick={{ fill: '#E0E0E0', fontSize: 10 }} />
              <YAxis tick={{ fill: '#8888AA', fontSize: 9 }} tickFormatter={(v) => v + '%'} width={30} />
              <Tooltip formatter={(v: number) => [v + '%', 'Probabilidad']} contentStyle={{ background: '#1C1C3A', border: '1px solid #2A2A4A', borderRadius: 8, fontSize: 11 }} />
              <Bar dataKey="value" fill="#D4AF37" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, PieChart, Pie, Tooltip } from 'recharts';
import type { PredictionResponse } from '../types';
import { formatHeight, formatProbability } from '../utils/api';

interface Props {
  prediction: PredictionResponse;
}

export default function PredictionResult({ prediction }: Props) {
  const { fighter_a_profile: a, fighter_b_profile: b, winner } = prediction;
  const aIsWinner = winner === prediction.fighter_a;

  const methodData = Object.entries(prediction.method_prediction).map(([name, value]) => ({
    name,
    value: Math.round(value * 100),
  }));

  const roundData = Object.entries(prediction.round_prediction).map(([name, value]) => ({
    name: name.replace('Round ', 'R'),
    value: Math.round(value * 100),
  }));

  const methodColors: Record<string, string> = {
    'KO/TKO': '#C8102E',
    'Submission': '#7F77DD',
    'Decision': '#378ADD',
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Winner Banner */}
      <div className="glass-card p-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-ufc-red/5 via-transparent to-blue-500/5" />
        <p className="text-ufc-muted text-sm mb-2 relative">Ganador predicho</p>
        <h2 className="text-3xl font-black text-white relative">{winner}</h2>
        <p className="text-ufc-gold text-2xl font-bold mt-1 relative">
          {formatProbability(prediction.winner_probability)}
        </p>
      </div>

      {/* Fighter Comparison */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-start">
        {/* Fighter A */}
        <div className={`glass-card p-5 ${aIsWinner ? 'border-ufc-red border-2' : ''}`}>
          <div className="text-center">
            <p className="text-xs text-ufc-red font-bold uppercase tracking-wider mb-2">Peleador A</p>
            <h3 className={`text-lg font-bold ${aIsWinner ? 'text-white' : 'text-ufc-muted'}`}>
              {a.name}
            </h3>
            <p className="text-ufc-muted text-sm">{a.record}</p>
            <p className={`text-2xl font-bold mt-2 ${aIsWinner ? 'text-ufc-red' : 'text-ufc-muted'}`}>
              {formatProbability(a.win_probability)}
            </p>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-ufc-muted">Altura</span><span>{formatHeight(a.height)}</span></div>
            <div className="flex justify-between"><span className="text-ufc-muted">Reach</span><span>{a.reach ? `${a.reach}"` : '--'}</span></div>
            <div className="flex justify-between"><span className="text-ufc-muted">Peso</span><span>{a.weight ? `${a.weight} lbs` : '--'}</span></div>
            <div className="flex justify-between"><span className="text-ufc-muted">Stance</span><span>{a.stance || '--'}</span></div>
          </div>
        </div>

        {/* VS */}
        <div className="flex items-center justify-center pt-16">
          <div className="w-14 h-14 rounded-full bg-ufc-border flex items-center justify-center">
            <span className="text-ufc-muted font-bold text-sm">VS</span>
          </div>
        </div>

        {/* Fighter B */}
        <div className={`glass-card p-5 ${!aIsWinner ? 'border-blue-500 border-2' : ''}`}>
          <div className="text-center">
            <p className="text-xs text-blue-400 font-bold uppercase tracking-wider mb-2">Peleador B</p>
            <h3 className={`text-lg font-bold ${!aIsWinner ? 'text-white' : 'text-ufc-muted'}`}>
              {b.name}
            </h3>
            <p className="text-ufc-muted text-sm">{b.record}</p>
            <p className={`text-2xl font-bold mt-2 ${!aIsWinner ? 'text-blue-400' : 'text-ufc-muted'}`}>
              {formatProbability(b.win_probability)}
            </p>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-ufc-muted">Altura</span><span>{formatHeight(b.height)}</span></div>
            <div className="flex justify-between"><span className="text-ufc-muted">Reach</span><span>{b.reach ? `${b.reach}"` : '--'}</span></div>
            <div className="flex justify-between"><span className="text-ufc-muted">Peso</span><span>{b.weight ? `${b.weight} lbs` : '--'}</span></div>
            <div className="flex justify-between"><span className="text-ufc-muted">Stance</span><span>{b.stance || '--'}</span></div>
          </div>
        </div>
      </div>

      {/* Probability Bar */}
      <div className="glass-card p-5">
        <p className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-3">Probabilidad de victoria</p>
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-ufc-red w-16 text-right">{formatProbability(a.win_probability)}</span>
          <div className="flex-1 h-4 bg-ufc-dark rounded-full overflow-hidden flex">
            <div className="prob-bar bg-ufc-red" style={{ width: `${a.win_probability * 100}%` }} />
            <div className="prob-bar bg-blue-500" style={{ width: `${b.win_probability * 100}%` }} />
          </div>
          <span className="text-sm font-bold text-blue-400 w-16">{formatProbability(b.win_probability)}</span>
        </div>
      </div>

      {/* Method & Round Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Method */}
        <div className="glass-card p-5">
          <p className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Método de victoria</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={methodData} layout="vertical" margin={{ left: 10, right: 30 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#8888AA', fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#E0E0E0', fontSize: 12 }} width={80} />
              <Tooltip formatter={(v: number) => [`${v}%`, 'Probabilidad']} contentStyle={{ background: '#1C1C3A', border: '1px solid #2A2A4A', borderRadius: 8 }} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {methodData.map((entry) => (
                  <Cell key={entry.name} fill={methodColors[entry.name] || '#888'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Decision vs Finish */}
        <div className="glass-card p-5">
          <p className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">¿Llega a decisión?</p>
          <div className="flex items-center gap-6">
            <ResponsiveContainer width="50%" height={160}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'Finish', value: Math.round(prediction.goes_to_decision.finish * 100) },
                    { name: 'Decisión', value: Math.round(prediction.goes_to_decision.decision * 100) },
                  ]}
                  cx="50%" cy="50%"
                  innerRadius={40} outerRadius={65}
                  dataKey="value"
                  strokeWidth={0}
                >
                  <Cell fill="#C8102E" />
                  <Cell fill="#378ADD" />
                </Pie>
                <Tooltip formatter={(v: number) => [`${v}%`]} contentStyle={{ background: '#1C1C3A', border: '1px solid #2A2A4A', borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-ufc-red" />
                <span className="text-sm">Finish: <strong>{Math.round(prediction.goes_to_decision.finish * 100)}%</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-sm">Decisión: <strong>{Math.round(prediction.goes_to_decision.decision * 100)}%</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Round Prediction */}
      {prediction.goes_to_decision.finish > 0.4 && (
        <div className="glass-card p-5">
          <p className="text-xs text-ufc-muted font-bold uppercase tracking-wider mb-4">Round de finalización (si es finish)</p>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={roundData} margin={{ left: 0, right: 10 }}>
              <XAxis dataKey="name" tick={{ fill: '#E0E0E0', fontSize: 12 }} />
              <YAxis tick={{ fill: '#8888AA', fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
              <Tooltip formatter={(v: number) => [`${v}%`, 'Probabilidad']} contentStyle={{ background: '#1C1C3A', border: '1px solid #2A2A4A', borderRadius: 8 }} />
              <Bar dataKey="value" fill="#D4AF37" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

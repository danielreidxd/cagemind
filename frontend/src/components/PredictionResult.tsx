import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, PieChart, Pie, Tooltip } from 'recharts';
import type { PredictionResponse } from '../types';
import { formatHeight, formatProbability } from '../utils/api';
import CardGenerator from './CardGenerator';

interface Props {
  prediction: PredictionResponse;
  eventName?: string;
}

export default function PredictionResult({ prediction, eventName }: Props) {
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
    'KO/TKO': '#B91C1C',
    'Submission': '#7C6DD8',
    'Decision': '#3B82B0',
  };

  const tooltipStyle = {
    background: '#161616',
    border: '1px solid #222222',
    borderRadius: 6,
    fontSize: 11,
  };

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Winner Banner */}
      <div className="glass-card p-6 text-center relative">
        <div className="absolute top-4 right-4 z-10">
          <CardGenerator prediction={prediction} eventName={eventName} />
        </div>
        <p className="text-[10px] font-semibold tracking-[2px] uppercase text-ufc-muted mb-1.5">Ganador predicho</p>
        <h2 className="text-[22px] font-extrabold text-white">{winner}</h2>
        <p className="text-ufc-gold text-[28px] font-extrabold mt-1">
          {formatProbability(prediction.winner_probability)}
        </p>
        {prediction.confidence && prediction.confidence !== 'HIGH' && (
          <span className={`text-[10px] font-semibold px-3 py-1 rounded mt-2 inline-block ${
            prediction.confidence === 'LOW'
              ? 'bg-red-900/30 text-red-400 border border-red-800/40'
              : 'bg-yellow-900/30 text-yellow-500 border border-yellow-800/40'
          }`}>
            {prediction.confidence === 'LOW' ? 'Confianza baja' : 'Confianza media'}
            {prediction.confidence_reason && (
              <span className="block text-[9px] font-normal mt-0.5 opacity-60">{prediction.confidence_reason}</span>
            )}
          </span>
        )}
      </div>

      {/* Probability Bar */}
      <div className="glass-card p-4">
        <div className="flex items-center justify-between mb-2.5">
          <span className="text-[13px] font-bold text-ufc-red-light">{formatProbability(a.win_probability)}</span>
          <span className="text-[10px] text-ufc-muted tracking-[1px] uppercase">Probabilidad</span>
          <span className="text-[13px] font-bold text-ufc-blue">{formatProbability(b.win_probability)}</span>
        </div>
        <div className="h-1.5 bg-ufc-border rounded-full overflow-hidden flex">
          <div className="h-full bg-ufc-red rounded-l-full transition-all duration-500" style={{ width: `${a.win_probability * 100}%` }} />
          <div className="h-full bg-ufc-blue rounded-r-full transition-all duration-500" style={{ width: `${b.win_probability * 100}%` }} />
        </div>
      </div>

      {/* Explanations */}
      {prediction.explanations && prediction.explanations.length > 0 && (
        <div className="glass-card p-4">
          <p className="card-title">Por que gana {winner}</p>
          <div className="space-y-2">
            {prediction.explanations.map((exp, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <span className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  i === 0 ? 'bg-ufc-gold/15 text-ufc-gold' : 'bg-ufc-border text-ufc-muted'
                }`}>{i + 1}</span>
                <p className="text-[12px] text-ufc-text/90 leading-relaxed">{exp.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fighter Comparison */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-start">
        {/* Fighter A */}
        <div className={`glass-card p-4 ${aIsWinner ? 'border-ufc-red' : ''}`} style={aIsWinner ? { borderWidth: '1.5px' } : {}}>
          <div className="text-center">
            <p className="text-[10px] font-semibold tracking-[2px] uppercase text-ufc-red-light mb-2">Peleador A</p>
            <h3 className={`text-[15px] font-bold ${aIsWinner ? 'text-white' : 'text-ufc-muted'}`}>{a.name}</h3>
            <p className="text-ufc-muted text-[12px]">{a.record}</p>
            <p className={`text-[20px] font-extrabold mt-2 ${aIsWinner ? 'text-ufc-red-light' : 'text-ufc-muted'}`}>
              {formatProbability(a.win_probability)}
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-ufc-border/50 space-y-1">
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Altura</span><span className="text-ufc-muted font-medium">{formatHeight(a.height)}</span></div>
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Reach</span><span className="text-ufc-muted font-medium">{a.reach ? `${a.reach}"` : '--'}</span></div>
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Peso</span><span className="text-ufc-muted font-medium">{a.weight ? `${a.weight} lbs` : '--'}</span></div>
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Stance</span><span className="text-ufc-muted font-medium">{a.stance || '--'}</span></div>
          </div>
        </div>

        {/* VS */}
        <div className="flex items-center justify-center pt-14">
          <div className="w-10 h-10 rounded-full border border-ufc-border-light flex items-center justify-center">
            <span className="text-ufc-muted font-bold text-[11px] tracking-wider">VS</span>
          </div>
        </div>

        {/* Fighter B */}
        <div className={`glass-card p-4 ${!aIsWinner ? 'border-ufc-blue' : ''}`} style={!aIsWinner ? { borderWidth: '1.5px' } : {}}>
          <div className="text-center">
            <p className="text-[10px] font-semibold tracking-[2px] uppercase text-ufc-blue mb-2">Peleador B</p>
            <h3 className={`text-[15px] font-bold ${!aIsWinner ? 'text-white' : 'text-ufc-muted'}`}>{b.name}</h3>
            <p className="text-ufc-muted text-[12px]">{b.record}</p>
            <p className={`text-[20px] font-extrabold mt-2 ${!aIsWinner ? 'text-ufc-blue' : 'text-ufc-muted'}`}>
              {formatProbability(b.win_probability)}
            </p>
          </div>
          <div className="mt-3 pt-3 border-t border-ufc-border/50 space-y-1">
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Altura</span><span className="text-ufc-muted font-medium">{formatHeight(b.height)}</span></div>
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Reach</span><span className="text-ufc-muted font-medium">{b.reach ? `${b.reach}"` : '--'}</span></div>
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Peso</span><span className="text-ufc-muted font-medium">{b.weight ? `${b.weight} lbs` : '--'}</span></div>
            <div className="flex justify-between text-[12px]"><span className="text-ufc-muted2">Stance</span><span className="text-ufc-muted font-medium">{b.stance || '--'}</span></div>
          </div>
        </div>
      </div>

      {/* Method & Decision Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Method */}
        <div className="glass-card p-4">
          <p className="card-title">Metodo de victoria</p>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={methodData} layout="vertical" margin={{ left: 5, right: 20 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#525252', fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#E8E8E8', fontSize: 11 }} width={75} />
              <Tooltip formatter={(v: number) => [`${v}%`, 'Probabilidad']} contentStyle={tooltipStyle} />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                {methodData.map((entry) => (
                  <Cell key={entry.name} fill={methodColors[entry.name] || '#525252'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Decision vs Finish */}
        <div className="glass-card p-4">
          <p className="card-title">Finish vs Decision</p>
          <div className="flex items-center gap-5 justify-center">
            <ResponsiveContainer width="45%" height={130}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'Finish', value: Math.round(prediction.goes_to_decision.finish * 100) },
                    { name: 'Decision', value: Math.round(prediction.goes_to_decision.decision * 100) },
                  ]}
                  cx="50%" cy="50%"
                  innerRadius={30} outerRadius={50}
                  dataKey="value"
                  strokeWidth={0}
                >
                  <Cell fill="#B91C1C" />
                  <Cell fill="#3B82B0" />
                </Pie>
                <Tooltip formatter={(v: number) => [`${v}%`]} contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-ufc-red" />
                <span className="text-[11px] text-ufc-muted">Finish <strong className="text-white">{Math.round(prediction.goes_to_decision.finish * 100)}%</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-ufc-blue" />
                <span className="text-[11px] text-ufc-muted">Decision <strong className="text-white">{Math.round(prediction.goes_to_decision.decision * 100)}%</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Round Prediction */}
      {prediction.goes_to_decision.finish > 0.4 && (
        <div className="glass-card p-4">
          <p className="card-title">Round de finalizacion (si es finish)</p>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={roundData} margin={{ left: 0, right: 10 }}>
              <XAxis dataKey="name" tick={{ fill: '#E8E8E8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#525252', fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
              <Tooltip formatter={(v: number) => [`${v}%`, 'Probabilidad']} contentStyle={tooltipStyle} />
              <Bar dataKey="value" fill="#C9A227" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
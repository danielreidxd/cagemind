import { useState } from 'react';
import type { Fighter } from '../types';
import type { PredictionResponse } from '../types';
import FighterSelector from '../components/FighterSelector';
import PredictionResult from '../components/PredictionResult';
import { predictFight } from '../utils/api';
import { useAnalytics } from '../hooks/useAnalytics';

export default function SandboxPage() {
  const [fighterA, setFighterA] = useState<Fighter | null>(null);
  const [fighterB, setFighterB] = useState<Fighter | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { trackPrediction } = useAnalytics();

  const canPredict = fighterA && fighterB && fighterA.name !== fighterB.name;

  async function handlePredict() {
    if (!fighterA || !fighterB) return;
    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
      const result = await predictFight(fighterA.name, fighterB.name);
      setPrediction(result);
      trackPrediction(fighterA.name, fighterB.name);
    } catch (e: any) {
      setError(e.message || 'Error al predecir');
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setFighterA(null);
    setFighterB(null);
    setPrediction(null);
    setError(null);
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-black tracking-tight">
          <span className="gold-gradient">Sandbox</span> de Predicción
        </h1>
        <p className="text-ufc-muted mt-2 text-lg">
          Selecciona dos peleadores y obtén una predicción completa con IA
        </p>
      </div>

      {/* Fighter Selection */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-start mb-8">
        <FighterSelector
          label="Peleador A"
          color="red"
          selected={fighterA}
          onSelect={setFighterA}
          onClear={() => { setFighterA(null); setPrediction(null); }}
        />

        <div className="flex items-center justify-center md:pt-10">
          <div className="w-12 h-12 rounded-full bg-ufc-border/50 flex items-center justify-center">
            <span className="text-ufc-muted font-bold text-xs">VS</span>
          </div>
        </div>

        <FighterSelector
          label="Peleador B"
          color="blue"
          selected={fighterB}
          onSelect={setFighterB}
          onClear={() => { setFighterB(null); setPrediction(null); }}
        />
      </div>

      {/* Action Buttons */}
      <div className="flex justify-center gap-4 mb-8">
        <button onClick={handlePredict} disabled={!canPredict || loading} className="btn-primary text-lg px-10">
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analizando...
            </span>
          ) : 'Predecir Pelea'}
        </button>
        {(fighterA || fighterB) && (
          <button onClick={handleReset} className="btn-secondary">
            Reiniciar
          </button>
        )}
      </div>

      {/* Same fighter error */}
      {fighterA && fighterB && fighterA.name === fighterB.name && (
        <div className="text-center text-ufc-red mb-4">
          Selecciona dos peleadores diferentes
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-card p-4 border-ufc-red border text-center mb-6">
          <p className="text-ufc-red">{error}</p>
        </div>
      )}

      {/* Results */}
      {prediction && <PredictionResult prediction={prediction} />}

      {/* Empty state */}
      {!fighterA && !fighterB && !prediction && (
        <div className="text-center py-16 text-ufc-muted">
          <div className="text-6xl mb-4 opacity-20">🥊</div>
          <p className="text-lg">Busca y selecciona dos peleadores para comenzar</p>
          <p className="text-sm mt-2">El modelo analiza 134 variables estadísticas para generar predicciones</p>
        </div>
      )}
    </div>
  );
}

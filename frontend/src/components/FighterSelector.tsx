import { useState, useRef, useEffect } from 'react';
import type { Fighter } from '../types';
import { useFighterSearch } from '../hooks/useFighterSearch';
import { formatRecord } from '../utils/api';

interface Props {
  label: string;
  color: 'red' | 'blue';
  selected: Fighter | null;
  onSelect: (fighter: Fighter) => void;
  onClear: () => void;
}

export default function FighterSelector({ label, color, selected, onSelect, onClear }: Props) {
  const { query, setQuery, results, loading } = useFighterSearch();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const borderColor = color === 'red' ? 'border-ufc-red' : 'border-blue-500';
  const accentColor = color === 'red' ? 'text-ufc-red' : 'text-blue-400';
  const bgAccent = color === 'red' ? 'bg-ufc-red/10' : 'bg-blue-500/10';

  if (selected) {
    return (
      <div className={`glass-card p-5 ${borderColor} border-2`}>
        <div className="flex items-center justify-between mb-3">
          <span className={`text-xs font-bold uppercase tracking-wider ${accentColor}`}>{label}</span>
          <button onClick={onClear} className="text-ufc-muted hover:text-white text-xs transition-colors">
            Cambiar
          </button>
        </div>
        <h3 className="text-xl font-bold text-white">{selected.name}</h3>
        <p className="text-ufc-muted mt-1">
          {formatRecord(selected.wins, selected.losses, selected.draws)} · {selected.weight_lbs || '--'} lbs · {selected.stance || '--'}
        </p>
      </div>
    );
  }

  return (
    <div ref={ref} className="relative">
      <div className={`glass-card p-5 ${open ? borderColor + ' border-2' : ''}`}>
        <span className={`text-xs font-bold uppercase tracking-wider ${accentColor} block mb-3`}>{label}</span>
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          placeholder="Buscar peleador..."
          className="input-search"
        />
        {loading && <p className="text-ufc-muted text-xs mt-2">Buscando...</p>}
      </div>

      {open && results.length > 0 && (
        <div className="absolute z-40 w-full mt-1 bg-ufc-gray border border-ufc-border rounded-lg shadow-2xl max-h-72 overflow-y-auto">
          {results.map((f) => (
            <button
              key={f.name}
              onClick={() => { onSelect(f); setOpen(false); setQuery(''); }}
              className={`w-full text-left px-4 py-3 hover:${bgAccent} transition-colors border-b border-ufc-border/50 last:border-0`}
            >
              <span className="font-medium text-white">{f.name}</span>
              <span className="text-ufc-muted text-sm ml-2">
                {formatRecord(f.wins, f.losses, f.draws)} · {f.weight_lbs || '--'} lbs
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

import { useState, useEffect, useRef } from 'react';
import type { Fighter } from '../types';
import { searchFighters } from '../utils/api';

export function useFighterSearch(debounceMs = 300) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Fighter[]>([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (query.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    timerRef.current = setTimeout(async () => {
      try {
        const data = await searchFighters(query);
        setResults(data.fighters);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, debounceMs);

    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [query, debounceMs]);

  return { query, setQuery, results, loading };
}

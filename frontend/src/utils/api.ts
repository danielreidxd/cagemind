import type { PredictionResponse, FighterSearchResult, FighterDetail, StatsResponse } from '../types';

const API_BASE = '/api';

export async function searchFighters(query: string, limit = 20): Promise<FighterSearchResult> {
  const res = await fetch(`${API_BASE}/fighters?search=${encodeURIComponent(query)}&limit=${limit}&min_fights=1`);
  if (!res.ok) throw new Error('Error buscando peleadores');
  return res.json();
}

export async function getFighterDetail(name: string): Promise<FighterDetail> {
  const res = await fetch(`${API_BASE}/fighters/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error('Peleador no encontrado');
  return res.json();
}

export async function predictFight(fighterA: string, fighterB: string): Promise<PredictionResponse> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fighter_a: fighterA, fighter_b: fighterB }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Error en predicción');
  }
  return res.json();
}

export async function getStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error('Error obteniendo stats');
  return res.json();
}

export async function getUpcoming(): Promise<any> {
  const res = await fetch(`${API_BASE}/upcoming`);
  if (!res.ok) throw new Error('Error obteniendo peleas próximas');
  return res.json();
}

export function formatRecord(wins: number, losses: number, draws: number): string {
  return `${wins}-${losses}-${draws}`;
}

export function formatHeight(inches: number | null): string {
  if (!inches) return '--';
  const ft = Math.floor(inches / 12);
  const in_ = Math.round(inches % 12);
  return `${ft}'${in_}"`;
}

export function formatProbability(prob: number): string {
  return `${(prob * 100).toFixed(1)}%`;
}

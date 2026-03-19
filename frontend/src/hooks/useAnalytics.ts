import { useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';

const API_BASE = import.meta.env.PROD
  ? 'https://web-production-2bc52.up.railway.app'
  : '/api';

function sendTrack(event_type: string, page?: string, detail?: string) {
  fetch(`${API_BASE}/analytics/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type, page, detail }),
  }).catch(() => {}); // Fire and forget
}

/**
 * Automatically tracks page views on route change.
 * Also exposes trackPrediction and trackSearch for manual use.
 */
export function useAnalytics() {
  const location = useLocation();

  // Auto-track page views
  useEffect(() => {
    const page = location.pathname === '/' ? 'proximamente' :
                 location.pathname.replace('/', '');
    sendTrack('page_view', page);
  }, [location.pathname]);

  const trackPrediction = useCallback((fighterA: string, fighterB: string) => {
    sendTrack('prediction', 'sandbox', `${fighterA} vs ${fighterB}`);
  }, []);

  const trackSearch = useCallback((query: string) => {
    if (query.length >= 2) {
      sendTrack('search', 'sandbox', query);
    }
  }, []);

  return { trackPrediction, trackSearch };
}

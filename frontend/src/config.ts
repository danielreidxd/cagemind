/**
 * Configuración centralizada del frontend.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || (
    import.meta.env.PROD
        ? 'https://web-production-2bc52.up.railway.app'  // fallback a Railway
        : '/api'  // en desarrollo usa el proxy de Vite
);

// Log para debug en consola
console.log('[Config] API_BASE:', API_BASE, '| Environment:', import.meta.env.MODE);

/**
 * Configuración centralizada del frontend.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || (
    import.meta.env.PROD
        ? 'https://web-production-2bc52.up.railway.app'
        : '/api'
);

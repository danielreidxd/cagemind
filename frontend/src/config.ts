/**
 * Configuración centralizada del frontend.
 * Todas las constantes globales deben definirse aquí.
 */

export const API_BASE = import.meta.env.PROD
    ? 'https://web-production-2bc52.up.railway.app'
    : '/api';

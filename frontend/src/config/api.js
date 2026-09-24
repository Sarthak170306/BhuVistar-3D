/**
 * API configuration for BhuVistaar 3D frontend.
 * Reads base URL from Vite environment variable with local fallback.
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

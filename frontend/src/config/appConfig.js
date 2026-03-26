export const SERVER_IP = import.meta.env.VITE_SERVER_IP || window.location.hostname || 'localhost'
const HAS_EXPLICIT_SERVER_ORIGIN = Boolean(import.meta.env.VITE_SERVER_ORIGIN)
const USE_RELATIVE_API =
  import.meta.env.VITE_USE_RELATIVE_API === 'true' ||
  (!HAS_EXPLICIT_SERVER_ORIGIN && window.location.port !== '8000')

export const SERVER_ORIGIN = import.meta.env.VITE_SERVER_ORIGIN || (USE_RELATIVE_API ? window.location.origin : `http://${SERVER_IP}:8000`)
export const API_BASE_PATH = import.meta.env.VITE_API_BASE_PATH || (USE_RELATIVE_API ? '/api' : '')
export const GITHUB_AUTH_URL = import.meta.env.VITE_GITHUB_AUTH_URL || `${SERVER_ORIGIN}${API_BASE_PATH}/auth/github/start`

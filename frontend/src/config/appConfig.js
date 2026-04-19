export const SERVER_IP = import.meta.env.VITE_SERVER_IP || window.location.hostname || 'localhost'
const HAS_EXPLICIT_SERVER_ORIGIN = Boolean(import.meta.env.VITE_SERVER_ORIGIN)
const DEFAULT_API_PORT = import.meta.env.VITE_API_PORT || '8000'
const USE_RELATIVE_API =
  import.meta.env.VITE_USE_RELATIVE_API === 'true' ||
  (!HAS_EXPLICIT_SERVER_ORIGIN && ['', '80', '443', DEFAULT_API_PORT].includes(window.location.port))

export const SERVER_ORIGIN = import.meta.env.VITE_SERVER_ORIGIN || (USE_RELATIVE_API ? window.location.origin : `http://${SERVER_IP}:${DEFAULT_API_PORT}`)
export const API_BASE_PATH = import.meta.env.VITE_API_BASE_PATH || '/api'
export const GITHUB_AUTH_URL = import.meta.env.VITE_GITHUB_AUTH_URL || `${SERVER_ORIGIN}${API_BASE_PATH}/auth/github/start`

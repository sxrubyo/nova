export const SERVER_IP = import.meta.env.VITE_SERVER_IP || window.location.hostname || 'localhost'
const IS_PROXY_ENV =
  window.location.port === '3005' ||
  window.location.protocol === 'https:' ||
  (window.location.port === '' && !['localhost', '127.0.0.1'].includes(window.location.hostname))

export const SERVER_ORIGIN = import.meta.env.VITE_SERVER_ORIGIN || (IS_PROXY_ENV ? window.location.origin : `http://${SERVER_IP}:8000`)
export const API_BASE_PATH = import.meta.env.VITE_API_BASE_PATH || (IS_PROXY_ENV ? '/api' : '')
export const GITHUB_AUTH_URL = import.meta.env.VITE_GITHUB_AUTH_URL || `${SERVER_ORIGIN}${API_BASE_PATH}/auth/github/start`

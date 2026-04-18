import { SERVER_ORIGIN, API_BASE_PATH } from '@/config/appConfig'

const BASE_URL = `${SERVER_ORIGIN}${API_BASE_PATH}`

export async function apiClient(endpoint, options = {}) {
  const apiKey = localStorage.getItem('nova_api_key') || ''
  const headers = {
    'Content-Type': 'application/json',
    'x-api-key': apiKey,
    ...options.headers,
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: options.credentials || 'include',
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const message =
      errorData.detail ||
      errorData.error?.message ||
      errorData.error ||
      response.statusText ||
      'API request failed'
    throw new Error(message)
  }

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    return response
  }

  return response.json()
}

export const api = {
  get: (endpoint, options = {}) => apiClient(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, data, options = {}) =>
    apiClient(endpoint, { ...options, method: 'POST', body: JSON.stringify(data) }),
  put: (endpoint, data, options = {}) =>
    apiClient(endpoint, { ...options, method: 'PUT', body: JSON.stringify(data) }),
  patch: (endpoint, data, options = {}) =>
    apiClient(endpoint, { ...options, method: 'PATCH', body: JSON.stringify(data) }),
  delete: (endpoint, options = {}) => apiClient(endpoint, { ...options, method: 'DELETE' }),
}

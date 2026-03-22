import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'

export const useFetch = (endpoint, options = {}) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.get(endpoint, options)
      setData(result)
    } catch (err) {
      setError(err.message || 'Error fetching data')
    } finally {
      setLoading(false)
    }
  }, [endpoint, JSON.stringify(options)])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}

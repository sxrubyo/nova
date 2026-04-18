import { useEffect } from 'react'
import { useDashboardStore } from '@/stores/app-stores'

export function useDashboard() {
  const fetchDashboardData = useDashboardStore((state) => state.fetchDashboardData)
  const store = useDashboardStore()

  useEffect(() => {
    fetchDashboardData()
  }, [fetchDashboardData])

  return store
}

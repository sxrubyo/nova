import { useEffect } from 'react'
import { useLedgerStore } from '@/stores/app-stores'

export function useLedger() {
  const fetchLedger = useLedgerStore((state) => state.fetchLedger)
  const store = useLedgerStore()

  useEffect(() => {
    fetchLedger()
  }, [fetchLedger])

  return store
}

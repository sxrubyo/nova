import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Download, Search } from 'lucide-react'
import { api } from '../utils/api'
import { API_BASE_PATH, SERVER_ORIGIN } from '../config/appConfig'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.04 } },
}

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
}

function Ledger() {
  const [logs, setLogs] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [verdict, setVerdict] = useState('all')
  const [loadError, setLoadError] = useState('')
  const [isExporting, setIsExporting] = useState(false)

  const loadLedger = useCallback(async () => {
    setLoadError('')
    try {
      const query = verdict === 'all' ? '' : `?verdict=${verdict}`
      const data = await api.get(`/ledger${query ? `${query}&limit=100` : '?limit=100'}`)
      setLogs(data)
    } catch (err) {
      setLoadError(err.message || 'Failed to load ledger')
    } finally {
      setIsLoading(false)
    }
  }, [verdict])

  useEffect(() => {
    loadLedger()
  }, [loadLedger])

  const filteredLogs = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    if (!query) return logs
    return logs.filter((log) => {
      const haystack = `${log.agent_name} ${log.action} ${log.own_hash} ${log.reason}`.toLowerCase()
      return haystack.includes(query)
    })
  }, [logs, searchTerm])

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const apiKey = localStorage.getItem('nova_api_key') || ''
      const response = await fetch(`${SERVER_ORIGIN}${API_BASE_PATH}/ledger/export?fmt=csv&limit=1000`, {
        headers: { 'x-api-key': apiKey },
      })
      if (!response.ok) {
        throw new Error('Failed to export ledger')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'nova-ledger.csv'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setLoadError(err.message || 'Failed to export ledger')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
      <motion.section variants={item} className="flex flex-col gap-5 rounded-[30px] border border-black/8 bg-[#fffdfa] p-7 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)] md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Audit ledger</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-[#111111] dark:text-white">Immutable record of governed actions</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-black/62 dark:text-white/62">
            This view is sourced from `/ledger` and supports live search plus CSV export from `/ledger/export`.
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={isExporting}
          className="inline-flex items-center gap-2 rounded-2xl bg-[#111111] px-5 py-3 text-sm font-semibold text-white transition hover:bg-black disabled:opacity-50"
        >
          <Download className="h-4 w-4" />
          {isExporting ? 'Exporting...' : 'Export CSV'}
        </button>
      </motion.section>

      {loadError && (
        <motion.div variants={item} className="rounded-[24px] border border-red-500/15 bg-red-500/8 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {loadError}
        </motion.div>
      )}

      <motion.section variants={item} className="overflow-hidden rounded-[30px] border border-black/8 bg-white shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <div className="flex flex-col gap-4 border-b border-black/8 px-6 py-5 dark:border-white/[0.06] md:flex-row md:items-center md:justify-between">
          <div className="relative w-full max-w-xl">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/32 dark:text-white/32" />
            <input
              type="text"
              placeholder="Search by action, agent, reason or hash..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-2xl border border-black/8 bg-[#f6f1e6] py-3 pl-11 pr-4 text-sm text-[#111111] outline-none transition focus:border-black/14 focus:bg-white dark:border-white/[0.07] dark:bg-white/[0.04] dark:text-white dark:placeholder:text-white/30 dark:focus:border-white/14 dark:focus:bg-white/[0.06]"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {['all', 'APPROVED', 'BLOCKED', 'ESCALATED'].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setIsLoading(true)
                  setVerdict(value)
                }}
                className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
                  verdict === value ? 'bg-[#111111] text-white dark:bg-white dark:text-[#111111]' : 'border border-black/8 bg-white text-black/58 hover:bg-[#f6f1e6] dark:border-white/[0.07] dark:bg-white/[0.04] dark:text-white/58 dark:hover:bg-white/[0.07]'
                }`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1040px] text-left">
            <thead className="border-b border-black/8 bg-[#f7f1e6] dark:border-white/[0.06] dark:bg-white/[0.03]">
              <tr className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">
                <th className="px-6 py-4">Timestamp</th>
                <th className="px-6 py-4">Agent</th>
                <th className="px-6 py-4">Action</th>
                <th className="px-6 py-4">Verdict</th>
                <th className="px-6 py-4">Risk</th>
                <th className="px-6 py-4">Score</th>
                <th className="px-6 py-4">Hash</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-10 text-center text-sm text-black/45 dark:text-white/45">Loading ledger...</td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-10 text-center text-sm text-black/45 dark:text-white/45">No ledger entries match the current filters.</td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="border-b border-black/8 last:border-b-0 dark:border-white/[0.06]">
                    <td className="px-6 py-4 text-sm text-black/54 dark:text-white/54">{formatDate(log.executed_at)}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-[#111111] dark:text-white">{log.agent_name}</td>
                    <td className="px-6 py-4 text-sm text-black/70 dark:text-white/70">{log.action}</td>
                    <td className="px-6 py-4">
                      <span className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${verdictBadge(log.verdict)}`}>
                        {log.verdict}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-black/62 dark:text-white/62">{log.risk_level}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-[#111111] dark:text-white">{log.score}</td>
                    <td className="px-6 py-4 font-mono text-xs text-black/46 dark:text-white/46">{truncateHash(log.own_hash)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.section>
    </motion.div>
  )
}

function verdictBadge(verdict) {
  switch (verdict) {
    case 'APPROVED':
      return 'bg-[#3ecf8e]/12 text-[#1e8a5c]'
    case 'BLOCKED':
      return 'bg-[#d84b42]/10 text-[#b73d34]'
    case 'ESCALATED':
      return 'bg-[#d59f2a]/10 text-[#a87410]'
    default:
      return 'bg-black/6 text-black/55'
  }
}

function formatDate(value) {
  if (!value) return 'No timestamp'
  return new Date(value).toLocaleString()
}

function truncateHash(value) {
  if (!value) return 'Unavailable'
  if (value.length <= 18) return value
  return `${value.slice(0, 8)}...${value.slice(-8)}`
}

export default Ledger

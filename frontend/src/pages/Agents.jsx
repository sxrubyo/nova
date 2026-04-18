import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertTriangle, Plus, Search, ShieldCheck, ScanSearch } from 'lucide-react'
import { api } from '../utils/api'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
}

function Agents() {
  const navigate = useNavigate()
  const [agents, setAgents] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [loadError, setLoadError] = useState('')

  const loadAgents = useCallback(async () => {
    setLoadError('')
    try {
      const data = await api.get('/stats/agents')
      setAgents(data)
    } catch (err) {
      setLoadError(err.message || 'Failed to load agents')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAgents()
  }, [loadAgents])

  const filteredAgents = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    if (!query) return agents
    return agents.filter((agent) => agent.agent_name?.toLowerCase().includes(query))
  }, [agents, searchTerm])

  const summary = useMemo(() => {
    const total = agents.length
    const avgApproval = total
      ? Math.round(agents.reduce((sum, agent) => sum + (agent.approval_rate || 0), 0) / total)
      : 0
    const watchlist = agents.filter((agent) => (agent.blocked || 0) > 0 || (agent.escalated || 0) > 0).length
    const avgScore = total
      ? Math.round(agents.reduce((sum, agent) => sum + (agent.avg_score || 0), 0) / total)
      : 0

    return { total, avgApproval, watchlist, avgScore }
  }, [agents])

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
      <motion.section variants={item} className="flex flex-col gap-5 rounded-[30px] border border-black/8 bg-[#fffdfa] p-7 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)] md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Agent registry</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-[#111111] dark:text-white">Governed agents running in this workspace</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-black/62 dark:text-white/62">
            Review the governed agents already operating here, or open Discovery first to scan the host and see which runtime you will bind before creating a new one.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => navigate('/dashboard/discover')}
            className="inline-flex items-center gap-2 rounded-2xl border border-black/10 bg-white px-5 py-3 text-sm font-semibold text-[#111111] transition hover:border-black/20 dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-white"
          >
            <ScanSearch className="h-4 w-4" />
            Scan runtimes
          </button>
          <button
            onClick={() => navigate('/dashboard/agents/new')}
            className="inline-flex items-center gap-2 rounded-2xl bg-[#111111] px-5 py-3 text-sm font-semibold text-white transition hover:bg-black"
          >
            <Plus className="h-4 w-4" />
            Create agent
          </button>
        </div>
      </motion.section>

      {loadError && (
        <motion.div variants={item} className="rounded-[24px] border border-red-500/15 bg-red-500/8 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {loadError}
        </motion.div>
      )}

      <div className="grid gap-5 md:grid-cols-4">
        <SummaryCard label="Total agents" value={summary.total} />
        <SummaryCard label="Avg approval" value={`${summary.avgApproval}%`} />
        <SummaryCard label="Watchlist" value={summary.watchlist} tone="warning" />
        <SummaryCard label="Avg score" value={summary.avgScore} />
      </div>

      <motion.section variants={item} className="overflow-hidden rounded-[30px] border border-black/8 bg-white shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <div className="border-b border-black/8 px-6 py-5 dark:border-white/[0.06]">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/32 dark:text-white/32" />
            <input
              type="text"
              placeholder="Search agent names..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-2xl border border-black/8 bg-[#f6f1e6] py-3 pl-11 pr-4 text-sm text-[#111111] outline-none transition focus:border-black/14 focus:bg-white dark:border-white/[0.07] dark:bg-white/[0.04] dark:text-white dark:placeholder:text-white/30 dark:focus:border-white/14 dark:focus:bg-white/[0.06]"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left">
            <thead className="border-b border-black/8 bg-[#f7f1e6] dark:border-white/[0.06] dark:bg-white/[0.03]">
              <tr className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">
                <th className="px-6 py-4">Agent</th>
                <th className="px-6 py-4">Actions</th>
                <th className="px-6 py-4">Approval</th>
                <th className="px-6 py-4">Score</th>
                <th className="px-6 py-4">Risk</th>
                <th className="px-6 py-4">Last action</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-sm text-black/45 dark:text-white/45">Loading agents...</td>
                </tr>
              ) : filteredAgents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-10 text-center text-sm text-black/45 dark:text-white/45">No agents match the current search.</td>
                </tr>
              ) : (
                filteredAgents.map((agent) => {
                  const watch = (agent.blocked || 0) > 0 || (agent.escalated || 0) > 0
                  return (
                    <tr key={agent.agent_name} className="border-b border-black/8 last:border-b-0 dark:border-white/[0.06]">
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                          <div className={`flex h-10 w-10 items-center justify-center rounded-2xl ${watch ? 'bg-[#d84b42]/10 text-[#b73d34]' : 'bg-[#3ecf8e]/10 text-[#1e8a5c]'}`}>
                            {watch ? <AlertTriangle className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-[#111111] dark:text-white">{agent.agent_name}</p>
                            <p className="mt-1 text-xs text-black/46 dark:text-white/46">{agent.blocked || 0} blocked · {agent.escalated || 0} escalated</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5 text-sm text-black/68 dark:text-white/68">{agent.total_actions}</td>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                          <div className="h-2 w-24 overflow-hidden rounded-full bg-black/6 dark:bg-white/8">
                            <div className="h-full rounded-full bg-[#3ecf8e]" style={{ width: `${Math.min(agent.approval_rate || 0, 100)}%` }} />
                          </div>
                          <span className="text-sm font-semibold text-[#111111] dark:text-white">{agent.approval_rate}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-5 text-sm font-semibold text-[#111111] dark:text-white">{agent.avg_score}</td>
                      <td className="px-6 py-5">
                        <span className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${watch ? 'bg-[#d59f2a]/10 text-[#a87410]' : 'bg-[#3ecf8e]/12 text-[#1e8a5c]'}`}>
                          {watch ? 'watch' : 'stable'}
                        </span>
                      </td>
                      <td className="px-6 py-5 text-sm text-black/54 dark:text-white/54">{formatDate(agent.last_action)}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </motion.section>
    </motion.div>
  )
}

function SummaryCard({ label, value, tone = 'default' }) {
  const toneClass = tone === 'warning' ? 'text-[#b73d34]' : 'text-[#111111]'

  return (
    <motion.div variants={item} className="rounded-[28px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">{label}</p>
      <p className={`mt-4 text-3xl font-semibold tracking-[-0.04em] ${toneClass}`}>{value}</p>
    </motion.div>
  )
}

function formatDate(value) {
  if (!value) return 'No activity yet'
  return new Date(value).toLocaleString()
}

export default Agents

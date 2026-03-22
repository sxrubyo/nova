import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Plus,
  ShieldCheck,
  Waves,
} from 'lucide-react'
import { api } from '../utils/api'
import { useLanguage } from '../context/LanguageContext'
import { useStream } from '../hooks/useStream'
import CreateAgentModal from '../components/CreateAgentModal'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
}

function Dashboard() {
  const { t } = useLanguage()
  const events = useStream()
  const [workspace, setWorkspace] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [ledger, setLedger] = useState([])
  const [risk, setRisk] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)

  const loadDashboard = useCallback(async () => {
    setLoadError('')
    try {
      const [workspaceData, alertData, ledgerData, riskData] = await Promise.all([
        api.get('/workspaces/me'),
        api.get('/alerts?resolved=false&limit=4'),
        api.get('/ledger?limit=6'),
        api.get('/stats/risk'),
      ])

      setWorkspace(workspaceData)
      setAlerts(alertData)
      setLedger(ledgerData)
      setRisk(riskData?.agents || [])
    } catch (err) {
      setLoadError(err.message || 'Failed to load dashboard')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  const stats = workspace?.stats
  const approvalRate = stats?.approval_rate ?? 0
  const avgScore = stats?.avg_score ?? 0
  const healthTone = approvalRate >= 90 ? 'healthy' : approvalRate >= 75 ? 'watch' : 'critical'

  const streamFeed = useMemo(() => {
    return events.slice(0, 4).map((event, index) => ({
      id: `${event.timestamp}-${index}`,
      type: event.type,
      timestamp: event.timestamp,
      label: event.payload?.message || event.payload?.agent_name || 'Live runtime event',
    }))
  }, [events])

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="h-48 animate-pulse rounded-[32px] bg-black/[0.04] dark:bg-[#0D0D0D]" />
        <div className="grid gap-5 md:grid-cols-4">
          {[1, 2, 3, 4].map((key) => (
            <div key={key} className="h-28 animate-pulse rounded-[28px] bg-black/[0.04] dark:bg-[#0D0D0D]" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8 pb-16">
      <CreateAgentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={loadDashboard}
      />

      <motion.section
        variants={item}
        className="overflow-hidden rounded-[34px] border border-black/8 bg-[#11151b] text-white shadow-[0_35px_100px_-50px_rgba(0,0,0,0.5)]"
      >
        <div className="grid gap-6 px-8 py-8 md:grid-cols-[1.1fr_0.9fr] md:px-10">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/7 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-white/70">
              <ShieldCheck className="h-3.5 w-3.5" />
              Runtime Governance
            </div>
            <h1 className="mt-6 max-w-2xl text-4xl font-semibold tracking-[-0.05em] text-white md:text-5xl">
              Operate agents from a live control surface, not from placeholders.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/68">
              This workspace is now wired to real Nova endpoints: stats, ledger, alerts, risk scoring, event stream, and agent creation.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <button
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-[#111111] transition hover:bg-[#f2f2f2]"
              >
                <Plus className="h-4 w-4" />
                Create agent
              </button>
              <button
                onClick={loadDashboard}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/8 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/12"
              >
                <Activity className="h-4 w-4" />
                Refresh runtime
              </button>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <SignalCard label="Approval rate" value={`${approvalRate}%`} hint="of governed actions approved" />
            <SignalCard label="Average score" value={`${avgScore}`} hint="current decision confidence" />
            <SignalCard label="Active agents" value={`${stats?.active_agents || 0}`} hint="tokens actively in circulation" />
            <SignalCard label="Pending alerts" value={`${stats?.alerts_pending || 0}`} hint="items requiring operator review" />
          </div>
        </div>
      </motion.section>

      {loadError && (
        <motion.div variants={item} className="rounded-[28px] border border-red-500/15 bg-red-500/8 px-5 py-4 text-sm text-red-700 dark:text-red-300">
          {loadError}
        </motion.div>
      )}

      <div className="grid gap-5 md:grid-cols-4">
        <StatCard title={t('total_actions')} value={stats?.total_actions || 0} subtitle="validated actions in ledger" />
        <StatCard title={t('security_blocks')} value={stats?.blocked || 0} subtitle="blocked by policy or anomaly" tone="warning" />
        <StatCard title={t('active_nodes')} value={stats?.active_agents || 0} subtitle="active governed agents" />
        <StatCard title={t('system_health')} value={healthTone === 'healthy' ? 'Stable' : healthTone === 'watch' ? 'Watch' : 'Critical'} subtitle={`${stats?.alerts_pending || 0} pending alerts`} tone={healthTone} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-[#fffdfa] p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Recent activity</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Latest governed actions</h2>
            </div>
            <span className="text-xs text-black/45 dark:text-white/42">{ledger.length} records</span>
          </div>

          <div className="mt-6 overflow-hidden rounded-[24px] border border-black/8 dark:border-transparent dark:bg-black/10">
            {ledger.length === 0 ? (
              <EmptyState
                title="No ledger entries yet"
                description="Create an agent or send validations to see live audit records."
              />
            ) : (
              ledger.map((entry) => (
                <div key={entry.id} className="grid gap-3 border-b border-black/8 px-5 py-4 last:border-b-0 md:grid-cols-[1.1fr_0.7fr_110px] md:items-center dark:border-white/[0.05]">
                  <div>
                    <p className="text-sm font-semibold text-[#111111] dark:text-white">{entry.action}</p>
                    <p className="mt-1 text-xs text-black/52 dark:text-white/52">{entry.agent_name} · {formatDate(entry.executed_at)}</p>
                  </div>
                  <div className="text-sm text-black/58 dark:text-white/58">
                    Score {entry.score} · {entry.risk_level}
                  </div>
                  <div className="flex items-center justify-start md:justify-end">
                    <span className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${verdictBadge(entry.verdict)}`}>
                      {entry.verdict}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </motion.section>

        <div className="space-y-6">
          <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Pending alerts</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Operator queue</h2>
              </div>
              <AlertTriangle className="h-5 w-5 text-[#b35a00]" />
            </div>

            <div className="mt-6 space-y-3">
              {alerts.length === 0 ? (
                <EmptyState title="No active alerts" description="The workspace currently has no unresolved alert conditions." compact />
              ) : (
                alerts.map((alert) => (
                  <div key={alert.id} className="rounded-[24px] border border-black/8 bg-[#fbf7ef] p-4 dark:border-transparent dark:bg-white/[0.03]">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-[#111111] dark:text-white">{alert.agent_name || 'Workspace alert'}</p>
                      <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${severityBadge(alert.severity)}`}>
                        {alert.severity}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-black/65 dark:text-white/68">{alert.message}</p>
                  </div>
                ))
              )}
            </div>
          </motion.section>

          <motion.section variants={item} className="rounded-[30px] border border-transparent bg-[#11151b] p-6 text-white shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/42">Live stream</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Runtime events</h2>
              </div>
              <Waves className="h-5 w-5 text-[#79d9ab]" />
            </div>
            <div className="mt-6 space-y-3">
              {streamFeed.length === 0 ? (
                <p className="rounded-[24px] border border-white/10 bg-white/6 px-4 py-4 text-sm text-white/64">
                  Waiting for streamed validation events from `/stream/events`.
                </p>
              ) : (
                streamFeed.map((event) => (
                  <div key={event.id} className="rounded-[24px] border border-transparent bg-white/[0.05] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/48">{event.type}</span>
                      <span className="text-[11px] text-white/42">{formatTime(event.timestamp)}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-white/84">{event.label}</p>
                  </div>
                ))
              )}
            </div>
          </motion.section>
        </div>
      </div>

      <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Risk profile</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Agents under observation</h2>
          </div>
          <ArrowUpRight className="h-5 w-5 text-black/35 dark:text-white/35" />
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {risk.length === 0 ? (
            <EmptyState
              title="No agent risk data yet"
              description="Risk scoring will appear after validations start reaching the ledger."
              compact
            />
          ) : (
            risk.slice(0, 3).map((agent) => (
              <div key={agent.agent_name} className="rounded-[24px] border border-black/8 bg-[#fffdfa] p-5 dark:border-transparent dark:bg-white/[0.03]">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[#111111] dark:text-white">{agent.agent_name}</p>
                    <p className="mt-1 text-xs text-black/48 dark:text-white/48">{agent.total} actions in last 24h</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${riskBadge(agent.risk_score)}`}>
                    {agent.risk_score >= 70 ? 'high' : agent.risk_score >= 40 ? 'watch' : 'low'}
                  </span>
                </div>
                <div className="mt-5 h-2 overflow-hidden rounded-full bg-black/6 dark:bg-white/8">
                  <div
                    className={`h-full rounded-full ${agent.risk_score >= 70 ? 'bg-[#d84b42]' : agent.risk_score >= 40 ? 'bg-[#d59f2a]' : 'bg-[#2f9d63]'}`}
                    style={{ width: `${Math.min(agent.risk_score, 100)}%` }}
                  />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                  <Metric label="Risk" value={`${agent.risk_score}`} />
                  <Metric label="Blocked" value={`${agent.blocked}`} />
                  <Metric label="Score" value={`${agent.avg_score}`} />
                </div>
              </div>
            ))
          )}
        </div>
      </motion.section>
    </motion.div>
  )
}

function StatCard({ title, value, subtitle, tone = 'default' }) {
  const toneClasses = {
    default: 'text-[#111111]',
    warning: 'text-[#b44235]',
    healthy: 'text-[#2f9d63]',
    watch: 'text-[#d59f2a]',
    critical: 'text-[#d84b42]',
  }

  return (
    <motion.div variants={item} className="rounded-[28px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
      <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">{title}</p>
      <p className={`mt-4 text-3xl font-semibold tracking-[-0.04em] ${toneClasses[tone]} ${tone === 'default' ? 'dark:text-white' : ''}`}>{value}</p>
      <p className="mt-2 text-sm leading-6 text-black/56 dark:text-white/56">{subtitle}</p>
    </motion.div>
  )
}

function SignalCard({ label, value, hint }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-white/6 p-5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/45">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-white/62">{hint}</p>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/40 dark:text-white/40">{label}</p>
      <p className="mt-2 text-lg font-semibold text-[#111111] dark:text-white">{value}</p>
    </div>
  )
}

function EmptyState({ title, description, compact = false }) {
  return (
    <div className={`rounded-[24px] border border-dashed border-black/10 bg-[#fbf7ef] dark:border-white/[0.06] dark:bg-white/[0.03] ${compact ? 'p-4' : 'p-5 md:col-span-3'}`}>
      <div className="flex items-start gap-3">
        <CheckCircle2 className="mt-0.5 h-4 w-4 text-[#2f9d63]" />
        <div>
          <p className="text-sm font-semibold text-[#111111] dark:text-white">{title}</p>
          <p className="mt-1 text-sm leading-6 text-black/58 dark:text-white/58">{description}</p>
        </div>
      </div>
    </div>
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

function severityBadge(severity) {
  switch (severity) {
    case 'critical':
      return 'bg-[#d84b42]/12 text-[#b73d34]'
    case 'high':
      return 'bg-[#cb6a2f]/12 text-[#9d501f]'
    case 'medium':
      return 'bg-[#d59f2a]/10 text-[#a87410]'
    default:
      return 'bg-[#3ecf8e]/12 text-[#1e8a5c]'
  }
}

function riskBadge(score) {
  if (score >= 70) return 'bg-[#d84b42]/12 text-[#b73d34]'
  if (score >= 40) return 'bg-[#d59f2a]/10 text-[#a87410]'
  return 'bg-[#3ecf8e]/12 text-[#1e8a5c]'
}

function formatDate(value) {
  if (!value) return 'No timestamp'
  return new Date(value).toLocaleString()
}

function formatTime(value) {
  if (!value) return 'now'
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default Dashboard

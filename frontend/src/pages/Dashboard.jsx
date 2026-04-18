import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  Brain,
  CheckCircle2,
  Clock3,
  KeyRound,
  NotebookPen,
  Plus,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Waves,
  Zap,
} from 'lucide-react'
import { api } from '../utils/api'
import { useLanguage } from '../context/LanguageContext'
import { useStream } from '../hooks/useStream'
import OperatorAssistant from '../components/OperatorAssistant'
import ProviderMark from '../components/brand/ProviderMark'
import { providerStatus } from '../lib/mock-data'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
}

function Dashboard() {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const events = useStream()
  const [workspace, setWorkspace] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [ledger, setLedger] = useState([])
  const [risk, setRisk] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

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

  const rankedRisk = useMemo(() => {
    return [...risk].sort((left, right) => (right.risk_score || 0) - (left.risk_score || 0))
  }, [risk])

  const watchedAgents = rankedRisk.filter((agent) => (agent.risk_score || 0) >= 40).length
  const latestEvent = streamFeed[0]

  const focusItems = [
    {
      label: 'Pending alerts',
      value: `${alerts.length}`,
      detail: alerts.length > 0 ? 'Needs operator review' : 'Queue is currently clear',
      tone: alerts.length > 0 ? 'warning' : 'healthy',
    },
    {
      label: 'Agents on watch',
      value: `${watchedAgents}`,
      detail: watchedAgents > 0 ? 'Higher-risk behavior detected' : 'No agents above watch threshold',
      tone: watchedAgents > 0 ? 'watch' : 'healthy',
    },
    {
      label: 'Approval rate',
      value: `${approvalRate}%`,
      detail: approvalRate >= 90 ? 'Governance is behaving cleanly' : 'Worth checking recent decisions',
      tone: healthTone,
    },
  ]

  const operatorCards = [
    {
      title: 'Scan runtimes before binding',
      description: 'Discovery shows which host runtime Nova can actually reach before you create a managed agent.',
      icon: ScanSearch,
      actionLabel: 'Open discovery',
      onClick: () => navigate('/dashboard/discover'),
    },
    {
      title: 'Create a governed agent',
      description: 'Use the full wizard so the operator sees workspace, runtime target, and execution location before creating anything.',
      icon: Bot,
      actionLabel: 'Open wizard',
      onClick: () => navigate('/dashboard/agents/new'),
    },
    {
      title: 'Talk with your agent',
      description: 'The assistant now exposes all supported providers and lets operators add their own API key by provider.',
      icon: Brain,
      detail: 'Use the panel on the right',
    },
    {
      title: 'Review the decision trail',
      description: 'Use the ledger and the live stream to understand what happened before touching the policy layer.',
      icon: NotebookPen,
      detail: 'Start with the activity feed below',
    },
  ]

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
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8 pb-20 xl:pr-[480px]">
      <OperatorAssistant
        workspaceName={workspace?.name || 'workspace'}
        onRefresh={loadDashboard}
      />

      <motion.section
        variants={item}
        className="overflow-hidden rounded-[36px] border border-black/8 bg-[linear-gradient(135deg,#11161d_0%,#18202a_62%,#10161d_100%)] text-white shadow-[0_45px_110px_-58px_rgba(0,0,0,0.6)]"
      >
        <div className="grid gap-6 px-7 py-7 md:px-9 md:py-9 xl:grid-cols-[1.02fr_0.98fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.07] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-white/72">
              <ShieldCheck className="h-3.5 w-3.5" />
              Operator dashboard
            </div>

            <h1 className="mt-6 max-w-2xl text-4xl font-semibold tracking-[-0.05em] text-white md:text-[3.3rem] md:leading-[1.02]">
              Govern agents from one clear runtime, not from scattered tools and guesswork.
            </h1>

            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/68">
              The workspace works best when people can understand what changed, what needs attention, and which model is being used without reading a manual first.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <button
                onClick={() => navigate('/dashboard/discover')}
                className="inline-flex items-center gap-2 rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-[#111111] transition hover:bg-[#f2f2f2]"
              >
                <ScanSearch className="h-4 w-4" />
                Scan runtimes
              </button>
              <button
                onClick={() => navigate('/dashboard/agents/new')}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.07] px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/[0.11]"
              >
                <Plus className="h-4 w-4" />
                Create agent
              </button>
            </div>

            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              <HeroSignal
                label="Workspace"
                value={workspace?.name || 'workspace'}
                copy="Connected to live stats, alerts, ledger, and streaming events."
              />
              <HeroSignal
                label="Latest event"
                value={latestEvent ? formatTime(latestEvent.timestamp) : 'Waiting'}
                copy={latestEvent?.label || 'No streamed runtime events yet.'}
              />
            </div>
          </div>

          <div className="grid gap-4">
            <div className="rounded-[30px] border border-white/10 bg-white/[0.05] p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/44">What needs attention</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">Operator brief</h2>
                </div>
                <Sparkles className="h-5 w-5 text-[#7fd9af]" />
              </div>

              <div className="mt-5 space-y-3">
                {focusItems.map((itemData) => (
                  <FocusRow key={itemData.label} item={itemData} />
                ))}
              </div>
            </div>

            <div className="rounded-[30px] border border-white/10 bg-white/[0.05] p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/44">Talk with your agent</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">Model control is now visible</h2>
                </div>
                <KeyRound className="h-5 w-5 text-[#f8cf5a]" />
              </div>

              <div className="mt-5 space-y-3 text-sm leading-6 text-white/70">
                <p>Select a provider, choose a model, and use the server key when available.</p>
                <p>If the server does not have a key, the operator can paste their own API key by provider without leaving the dashboard.</p>
                <p className="text-white/52">The assistant panel on the right is the model cockpit.</p>
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      {loadError && (
        <motion.div variants={item} className="rounded-[28px] border border-red-500/15 bg-red-500/8 px-5 py-4 text-sm text-red-700 dark:text-red-300">
          {loadError}
        </motion.div>
      )}

      <div className="grid gap-5 md:grid-cols-4">
        <StatCard title={t('total_actions')} value={stats?.total_actions || 0} subtitle="validated actions recorded in the ledger" />
        <StatCard title={t('security_blocks')} value={stats?.blocked || 0} subtitle="blocked by policy or anomaly detection" tone="warning" />
        <StatCard title={t('active_nodes')} value={stats?.active_agents || 0} subtitle="active governed agents in circulation" />
        <StatCard
          title={t('system_health')}
          value={healthTone === 'healthy' ? 'Stable' : healthTone === 'watch' ? 'Watch' : 'Critical'}
          subtitle={`${stats?.alerts_pending || 0} items may need review`}
          tone={healthTone}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {operatorCards.map((card) => (
          <OperatorCard key={card.title} card={card} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-[#fffdfa] p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Recent decisions</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Latest governed actions</h2>
            </div>
            <span className="text-xs text-black/45 dark:text-white/42">{ledger.length} records</span>
          </div>

          <div className="mt-6 overflow-hidden rounded-[24px] border border-black/8 dark:border-transparent dark:bg-black/10">
            {ledger.length === 0 ? (
              <EmptyState
                title="No ledger entries yet"
                description="Create an agent or send validations to see live audit records appear here."
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
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Operator queue</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Alerts that need attention</h2>
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
                <p className="rounded-[24px] border border-white/10 bg-white/[0.06] px-4 py-4 text-sm text-white/64">
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

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Risk profile</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Agents under observation</h2>
            </div>
            <ArrowUpRight className="h-5 w-5 text-black/35 dark:text-white/35" />
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {rankedRisk.length === 0 ? (
              <EmptyState
                title="No agent risk data yet"
                description="Risk scoring will appear after validations start reaching the ledger."
                compact
              />
            ) : (
              rankedRisk.slice(0, 3).map((agent) => (
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

        <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-[linear-gradient(135deg,#fffdfa_0%,#f4eee3_100%)] p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[linear-gradient(135deg,#131921_0%,#10151b_100%)] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/42 dark:text-white/42">Model access</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Talk with your agent, with more options</h2>
            </div>
            <Zap className="h-5 w-5 text-[#cf9834]" />
          </div>

          <p className="mt-4 text-sm leading-7 text-black/65 dark:text-white/68">
            The assistant now exposes all supported providers. If a provider has a server key, the operator can use it immediately. If not, the operator can paste their own key inside the dashboard.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <ProviderSurface
              title="Full provider lane"
              description="The assistant now exposes the full Nova gateway with real provider marks, real model names, and clear default routes."
              providers={providerStatus}
              tone="light"
            />
            <ProviderSurface
              title="Default model routes"
              description="Operators can see the exact default model Nova will select first for every provider before sending a prompt."
              chips={providerStatus.map((provider) => `${provider.name} · ${provider.defaultModelLabel}`)}
              tone="light"
            />
          </div>

          <div className="mt-4 rounded-[24px] border border-black/8 bg-white/70 px-4 py-4 dark:border-white/[0.06] dark:bg-white/[0.04]">
            <div className="flex items-start gap-3">
              <Clock3 className="mt-0.5 h-4 w-4 text-[#cf9834]" />
              <p className="text-sm leading-6 text-black/65 dark:text-white/66">
                API keys entered by the operator are stored locally in the browser by provider, so the flow stays fast without forcing a server-side secret for every model.
              </p>
            </div>
          </div>
        </motion.section>
      </div>
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

function HeroSignal({ label, value, copy }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.06] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/44">{label}</p>
      <p className="mt-3 text-xl font-semibold tracking-[-0.03em] text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-white/62">{copy}</p>
    </div>
  )
}

function FocusRow({ item }) {
  const toneClasses = {
    healthy: 'bg-[#3ecf8e]/12 text-[#8fe4ba]',
    watch: 'bg-[#d59f2a]/12 text-[#f6d26a]',
    warning: 'bg-[#d46d34]/12 text-[#f4b06b]',
    critical: 'bg-[#d84b42]/12 text-[#f5988f]',
  }

  return (
    <div className="flex items-start justify-between gap-4 rounded-[24px] border border-white/10 bg-black/10 px-4 py-4">
      <div>
        <p className="text-sm font-semibold text-white">{item.label}</p>
        <p className="mt-1 text-sm leading-6 text-white/60">{item.detail}</p>
      </div>
      <span className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${toneClasses[item.tone]}`}>
        {item.value}
      </span>
    </div>
  )
}

function OperatorCard({ card }) {
  const Icon = card.icon

  return (
    <motion.div variants={item} className="rounded-[30px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-black/[0.04] dark:bg-white/[0.04]">
        <Icon className="h-5 w-5 text-[#111111] dark:text-white" />
      </div>
      <h3 className="mt-5 text-2xl font-semibold tracking-[-0.04em] text-[#111111] dark:text-white">{card.title}</h3>
      <p className="mt-3 text-sm leading-7 text-black/60 dark:text-white/62">{card.description}</p>

      {card.onClick ? (
        <button
          onClick={card.onClick}
          className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-black px-4 py-3 text-sm font-semibold text-white transition hover:opacity-90 dark:bg-white dark:text-[#111111]"
        >
          <Plus className="h-4 w-4" />
          {card.actionLabel}
        </button>
      ) : (
        <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-black/8 bg-[#fbf7ef] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-black/55 dark:border-white/[0.06] dark:bg-white/[0.04] dark:text-white/58">
          {card.detail}
        </div>
      )}
    </motion.div>
  )
}

function ProviderSurface({ title, description, providers = [], chips = [], tone = 'light' }) {
  const classes = tone === 'dark'
    ? 'border-transparent bg-[#11151b] text-white'
    : 'border-black/8 bg-white/75 text-[#111111] dark:border-white/[0.06] dark:bg-white/[0.03] dark:text-white'
  const rowClasses = tone === 'dark'
    ? 'border-white/10 bg-white/[0.05]'
    : 'border-black/8 bg-black/[0.03] dark:border-white/10 dark:bg-white/[0.05]'

  return (
    <div className={`rounded-[26px] border p-5 ${classes}`}>
      <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${tone === 'dark' ? 'text-white/42' : 'text-black/42 dark:text-white/42'}`}>{title}</p>
      <p className={`mt-3 text-sm leading-7 ${tone === 'dark' ? 'text-white/64' : 'text-black/60 dark:text-white/62'}`}>{description}</p>

      {providers.length > 0 && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {providers.map((provider) => (
            <div key={provider.name} className={`flex items-center gap-4 rounded-2xl border px-4 py-3 ${rowClasses}`}>
              <div className="flex min-w-0 items-center gap-3">
                <ProviderMark
                  src={provider.logo}
                  alt={`${provider.name} logo`}
                  frameClassName="h-16 w-16 rounded-[20px] p-3"
                  imageClassName="h-8 w-8"
                />
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{provider.name}</div>
                  <div className={`mt-1 truncate text-[11px] ${tone === 'dark' ? 'text-white/52' : 'text-black/48 dark:text-white/52'}`}>
                    {provider.defaultModelLabel}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {chips.length > 0 && (
        <div className="mt-5 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <span
              key={chip}
              className={`rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${tone === 'dark' ? 'bg-white/[0.08] text-white/72' : 'bg-black/[0.05] text-black/58 dark:bg-white/[0.05] dark:text-white/68'}`}
            >
              {chip}
            </span>
          ))}
        </div>
      )}
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

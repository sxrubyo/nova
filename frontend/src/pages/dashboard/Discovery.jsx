import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'
import { ArrowRight, Bot, BookOpen, Boxes, CheckCircle2, Cpu, Link2, ScanSearch, SearchX, ShieldCheck, TerminalSquare, Users, Workflow } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { Badge, Button, Card, CardContent, CardHeader, EmptyState, Modal, NovaLogo, ProgressBar, SparkLine } from '@/components/ui'
import { useDiscovery } from '@/hooks/useDiscovery'
import { useNovaEvents } from '@/hooks/useNovaEvents'
import { formatRelativeTime } from '@/lib/utils'

const iconMap = {
  terminal: TerminalSquare,
  workflow: Workflow,
  claw: Bot,
  chain: Link2,
  users: Users,
  container: Boxes,
  cpu: Cpu,
  code: TerminalSquare,
  microsoft: Bot,
}

const typeOptions = [
  { value: 'all', label: 'All' },
  { value: 'assistants', label: 'Assistants' },
  { value: 'frameworks', label: 'Frameworks' },
  { value: 'workflows', label: 'Workflows' },
]

const statusOptions = [
  { value: 'all', label: 'All status' },
  { value: 'connected', label: 'Connected' },
  { value: 'running', label: 'Running' },
  { value: 'idle', label: 'Idle' },
]

const sortOptions = [
  { value: 'confidence', label: 'Confidence' },
  { value: 'name', label: 'Name' },
  { value: 'type', label: 'Type' },
]

const onboardingStorageKey = 'nova_discovery_onboarding_complete'
const onboardingSteps = [
  {
    title: 'Welcome to Agent Discovery',
    body: 'Nova scans this host and only surfaces runtimes it can verify with concrete evidence. Weak guesses stay hidden.',
    checklist: ['Discovery is local to the host.', 'Only supported runtime fingerprints are evaluated.', 'Results feed directly into Nova governance.'],
  },
  {
    title: 'What Nova checks',
    body: 'The scanner combines config paths, package managers, processes, ports, and health probes. A single weak signal is not enough.',
    checklist: ['VS Code extensions and config directories', 'Processes, ports, and runtime health endpoints', 'Docker containers, npm packages, and pip packages'],
  },
  {
    title: 'Ready to scan',
    body: 'Start a strict scan now. Once a runtime is confirmed, you can connect it to Nova and keep its actions under policy control.',
    checklist: ['Review evidence counts before connecting', 'Use discovery help if you need supported-runtime details', 'Run another scan after installing a new runtime'],
  },
]

function classifyType(agent) {
  if (agent.fingerprint_key === 'n8n' || agent.type === 'workflow_engine') return 'workflows'
  if (['cli_agent', 'code_interpreter'].includes(agent.type)) return 'assistants'
  return 'frameworks'
}

function classifyStatus(agent) {
  if (agent.metadata?.connected) return 'connected'
  if (agent.is_running) return 'running'
  return 'idle'
}

function summarizeAgents(agents) {
  if (!agents.length) {
    return 'No confirmed runtimes yet. Nova now hides weak matches until the host produces enough evidence.'
  }

  const names = agents.map((agent) => agent.name)
  if (names.length <= 3) {
    return `Confirmed on this host: ${names.join(', ')}.`
  }

  return `Confirmed on this host: ${names.slice(0, 3).join(', ')} and ${names.length - 3} more.`
}

function DiscoveryOnboarding({ open, step, onNext, onBack, onStart, onOpenChange }) {
  const currentStep = onboardingSteps[step]

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={currentStep.title}
      description={currentStep.body}
      size="lg"
      headerAlign="center"
    >
      <div className="grid gap-6 lg:grid-cols-[0.88fr_1.12fr]">
        <div className="rounded-[28px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(0,212,170,0.18),transparent_48%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-6 text-center">
          <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Step {step + 1} of {onboardingSteps.length}</div>
          <div className="mt-6">
            <NovaLogo variant="full" size={54} animated />
          </div>
          <div className="mt-8 space-y-3">
            {onboardingSteps.map((item, index) => (
              <div
                key={item.title}
                className={`rounded-[20px] border px-4 py-3 text-sm ${
                  index === step
                    ? 'border-nova-accent/40 bg-nova-accent/12 text-white'
                    : 'border-white/10 bg-white/[0.03] text-nova-text-secondary'
                }`}
              >
                {item.title}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {currentStep.checklist.map((item) => (
            <div key={item} className="flex items-start gap-3 rounded-[22px] border border-white/10 bg-white/[0.03] px-4 py-3">
              <CheckCircle2 className="mt-0.5 h-4.5 w-4.5 shrink-0 text-nova-success" />
              <div className="text-sm leading-6 text-nova-text-secondary">{item}</div>
            </div>
          ))}

          <div className="flex flex-wrap items-center justify-between gap-3 pt-4">
            <Button variant="outline" onClick={onBack} disabled={step === 0}>
              Back
            </Button>
            <div className="flex items-center gap-3">
              <Button variant="ghost" onClick={() => onOpenChange(false)}>
                Skip
              </Button>
              {step < onboardingSteps.length - 1 ? (
                <Button onClick={onNext}>
                  Next
                  <ArrowRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={onStart}>
                  <ScanSearch className="h-4 w-4" />
                  Start scanning
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  )
}

function RadarVisual({ agents = [], isScanning = false }) {
  const size = 420
  const center = size / 2
  const visibleAgents = agents.slice(0, 8)

  return (
    <div className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_center,rgba(0,212,170,0.10),transparent_45%),linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01))] p-6">
      <svg viewBox={`0 0 ${size} ${size}`} className="mx-auto aspect-square w-full max-w-[420px]">
        {[72, 128, 184].map((radius) => (
          <circle key={radius} cx={center} cy={center} r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeDasharray="6 10" />
        ))}
        <line x1={center} y1="24" x2={center} y2={size - 24} stroke="rgba(255,255,255,0.05)" />
        <line x1="24" y1={center} x2={size - 24} y2={center} stroke="rgba(255,255,255,0.05)" />
        {isScanning && (
          <motion.circle
            cx={center}
            cy={center}
            r="12"
            fill="none"
            stroke="rgba(0,212,170,0.7)"
            initial={{ r: 12, opacity: 0.8 }}
            animate={{ r: 178, opacity: 0 }}
            transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.8, ease: 'easeOut' }}
          />
        )}
        {visibleAgents.map((agent, index) => {
          const angle = (Math.PI * 2 * index) / Math.max(visibleAgents.length, 1) - Math.PI / 2
          const radius = 82 + (index % 3) * 42 + Math.round((agent.confidence || 0.5) * 36)
          const x = center + Math.cos(angle) * radius
          const y = center + Math.sin(angle) * radius
          return (
            <g key={agent.agent_key}>
              <motion.circle
                cx={x}
                cy={y}
                r="10"
                fill={agent.color || '#00D4AA'}
                initial={{ scale: 0.85, opacity: 0.6 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.35, delay: index * 0.05 }}
              />
              <motion.circle
                cx={x}
                cy={y}
                r="18"
                fill="none"
                stroke={agent.color || '#00D4AA'}
                initial={{ opacity: 0.45, scale: 0.85 }}
                animate={{ opacity: agent.metadata?.connected ? 0.6 : 0.24, scale: 1.05 }}
                transition={{ repeat: Number.POSITIVE_INFINITY, repeatType: 'reverse', duration: 1.8 + index * 0.2 }}
              />
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function AgentMark({ agent }) {
  const [imageFailed, setImageFailed] = useState(false)
  const Icon = iconMap[agent.icon] || Bot
  const logoPath = agent.metadata?.logo_path
  const showImage = Boolean(logoPath) && !imageFailed

  return (
    <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04]">
      {showImage ? (
        <img
          src={logoPath}
          alt={`${agent.name} logo`}
          className="h-7 w-7 object-contain"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <Icon className="h-5 w-5" style={{ color: agent.color || '#00D4AA' }} />
      )}
    </div>
  )
}

function ScanChecklist({ agents = [], isScanning = false }) {
  const steps = [
    {
      label: 'Configuration footprints',
      done: agents.some((agent) => agent.detection_methods?.includes('config_file')),
    },
    {
      label: 'Installed binaries and packages',
      done: agents.some((agent) => (agent.detection_methods || []).some((method) => ['binary', 'pip_package', 'npm_package'].includes(method))),
    },
    {
      label: 'Running runtimes and health checks',
      done: agents.some((agent) => (agent.detection_methods || []).some((method) => ['process', 'port', 'docker'].includes(method))),
    },
    {
      label: 'Confidence threshold confirmed',
      done: agents.length > 0,
    },
  ]

  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const isActive = isScanning && !step.done && index === steps.findIndex((item) => !item.done)
        return (
          <div key={step.label} className="flex items-center justify-between rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="text-sm text-nova-text-primary">{step.label}</div>
            <div className="text-xs uppercase tracking-[0.18em] text-nova-text-secondary">
              {step.done ? 'Done' : isActive ? 'Running' : 'Pending'}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function DiscoveryCard({ agent, onConnect, onManage, isConnecting }) {
  const confidence = Math.round((agent.confidence || 0) * 100)
  const matchedSignals = agent.metadata?.matched_signals || agent.detection_methods?.length || 0
  const requiredMatches = agent.metadata?.required_matches || 1
  const supportedSignals = agent.metadata?.supported_signals || matchedSignals
  const evidence = (agent.metadata?.evidence || []).slice(0, 3)

  return (
    <Card
      variant="interactive"
      className={agent.metadata?.connected ? 'border-nova-accent/50 shadow-glow' : 'border-dashed border-white/16'}
    >
      <CardHeader>
        <div className="flex items-center gap-3">
          <AgentMark agent={agent} />
          <div>
            <div className="text-lg font-semibold text-white">{agent.name}</div>
            <div className="mt-1 text-xs uppercase tracking-[0.18em] text-nova-text-secondary">{agent.type}</div>
          </div>
        </div>
        <Badge variant={agent.metadata?.connected ? 'success' : agent.is_running ? 'info' : 'outline'} dot>
          {agent.metadata?.connected ? 'Connected' : agent.is_running ? 'Running' : 'Detected'}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 text-sm text-nova-text-secondary">
          <div>
            Evidence: <span className="text-white">{matchedSignals}/{supportedSignals} signals</span>
          </div>
          <div>
            Threshold: <span className="text-white">{requiredMatches} required</span>
          </div>
          <div>
            Detection: <span className="text-white">{(agent.detection_methods || []).join(' + ')}</span>
          </div>
        </div>

        <ProgressBar value={confidence} tone={agent.metadata?.connected ? 'success' : 'accent'} label="Confidence" />

        <div className="space-y-2 rounded-[22px] border border-white/10 bg-white/[0.03] p-3">
          {evidence.map((item) => (
            <div key={`${agent.agent_key}-${item.method}-${item.detail}`} className="flex items-start justify-between gap-3 text-xs">
              <div className="min-w-0 text-nova-text-secondary">
                <span className="uppercase tracking-[0.16em] text-white/72">{item.method}</span>
                <div className="mt-1 truncate">{item.detail}</div>
              </div>
              <span className="shrink-0 text-white">{Math.round((item.confidence || 0) * 100)}%</span>
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          {agent.metadata?.connected ? (
            <Button variant="secondary" fullWidth onClick={onManage}>Manage</Button>
          ) : (
            <Button fullWidth loading={isConnecting} onClick={onConnect}>Connect</Button>
          )}
          <Button variant="outline" fullWidth onClick={onManage}>View details</Button>
        </div>
      </CardContent>
    </Card>
  )
}

function DiscoveryCenter() {
  const navigate = useNavigate()
  const {
    agents,
    connectedAgents,
    isLoading,
    isScanning,
    error,
    lastScanAt,
    durationMs,
    scanNow,
    connectAgent,
  } = useDiscovery()
  const { lastEvent } = useNovaEvents()
  const [connectingAgentKey, setConnectingAgentKey] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('confidence')
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [onboardingStep, setOnboardingStep] = useState(0)
  const liveToastsReady = useRef(false)
  const seenEvents = useRef(new Set())

  useEffect(() => {
    const timer = window.setTimeout(() => {
      liveToastsReady.current = true
    }, 1500)
    return () => window.clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (window.localStorage.getItem(onboardingStorageKey) === 'true') return
    setShowOnboarding(true)
  }, [])

  useEffect(() => {
    if (!lastEvent || !liveToastsReady.current) return

    const payload = lastEvent.payload || {}
    const eventKey = `${lastEvent.type}:${payload.agent_key || payload.name || 'unknown'}:${lastEvent.timestamp || 'now'}`
    if (seenEvents.current.has(eventKey)) return
    seenEvents.current.add(eventKey)

    if (lastEvent.type === 'agent_discovered') {
      toast.custom((toastInstance) => (
        <div
          className={`pointer-events-auto flex w-[360px] items-center justify-between gap-4 rounded-[24px] border border-white/10 bg-[#11161d] px-4 py-3 shadow-float transition duration-200 ${
            toastInstance.visible ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0'
          }`}
        >
          <div>
            <div className="text-sm font-semibold text-white">New runtime discovered</div>
            <div className="mt-1 text-sm text-nova-text-secondary">{payload.name || 'Agent'} was confirmed on this host.</div>
          </div>
          <button
            className="rounded-full border border-white/10 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:border-nova-accent hover:text-nova-accent"
            onClick={() => {
              toast.dismiss(toastInstance.id)
              navigate('/dashboard/discover')
            }}
          >
            View
          </button>
        </div>
      ))
    }
    if (lastEvent.type === 'agent_lost') {
      toast.custom((toastInstance) => (
        <div
          className={`pointer-events-auto flex w-[360px] items-center gap-4 rounded-[24px] border border-nova-warning/20 bg-[#11161d] px-4 py-3 shadow-float transition duration-200 ${
            toastInstance.visible ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0'
          }`}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-nova-warning/12 text-nova-warning">!</div>
          <div>
            <div className="text-sm font-semibold text-white">Runtime no longer detected</div>
            <div className="mt-1 text-sm text-nova-text-secondary">{payload.name || 'Agent'} is no longer reachable from this host.</div>
          </div>
        </div>
      ))
    }
  }, [lastEvent, navigate])

  const filteredAgents = useMemo(() => {
    const filtered = agents.filter((agent) => {
      if (typeFilter !== 'all' && classifyType(agent) !== typeFilter) return false
      if (statusFilter !== 'all' && classifyStatus(agent) !== statusFilter) return false
      return true
    })

    return [...filtered].sort((left, right) => {
      if (sortBy === 'name') return left.name.localeCompare(right.name)
      if (sortBy === 'type') return left.type.localeCompare(right.type) || left.name.localeCompare(right.name)
      return (right.confidence || 0) - (left.confidence || 0)
    })
  }, [agents, sortBy, statusFilter, typeFilter])

  const connectedCount = connectedAgents.length
  const runningCount = agents.filter((agent) => agent.is_running).length
  const summary = summarizeAgents(agents)

  const handleConnect = async (agentKey) => {
    setConnectingAgentKey(agentKey)
    try {
      await connectAgent(agentKey)
      toast.success('Agent connected to Nova')
    } catch (connectError) {
      toast.error(connectError.message || 'Unable to connect agent')
    } finally {
      setConnectingAgentKey('')
    }
  }

  const handleOnboardingOpenChange = (open) => {
    setShowOnboarding(open)
    if (!open && typeof window !== 'undefined') {
      window.localStorage.setItem(onboardingStorageKey, 'true')
    }
  }

  const handleScanNow = async () => {
    const toastId = toast.loading('Scanning host evidence...')
    try {
      const response = await scanNow()
      const confirmedAgents = response?.agents || []
      if (confirmedAgents.length > 0) {
        toast.success(
          `${confirmedAgents.length} ${confirmedAgents.length === 1 ? 'runtime was' : 'runtimes were'} confirmed on this host.`,
          { id: toastId },
        )
      } else {
        toast.success('Scan complete. Nova did not confirm any supported runtime on this host.', { id: toastId })
      }
      return response
    } catch (scanError) {
      toast.error(scanError.message || 'Discovery scan failed', { id: toastId })
      throw scanError
    }
  }

  const handleStartFromOnboarding = async () => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(onboardingStorageKey, 'true')
    }
    setShowOnboarding(false)
    await handleScanNow()
  }

  return (
    <div className="space-y-8">
      <DiscoveryOnboarding
        open={showOnboarding}
        step={onboardingStep}
        onOpenChange={handleOnboardingOpenChange}
        onBack={() => setOnboardingStep((current) => Math.max(0, current - 1))}
        onNext={() => setOnboardingStep((current) => Math.min(onboardingSteps.length - 1, current + 1))}
        onStart={handleStartFromOnboarding}
      />

      <PageHeader
        eyebrow="Agent Discovery"
        title="Nova confirms only the runtimes this host can actually prove"
        description="Weak signals are filtered out. Discovery now requires enough evidence before an agent appears in the control plane."
        action={
          <div className="flex items-center gap-3">
            <Badge variant="outline">
              Last scan: {lastScanAt ? formatRelativeTime(lastScanAt) : 'Pending'}
            </Badge>
            <Button variant="outline" onClick={() => navigate('/dashboard/help/discovery')}>
              <BookOpen className="h-4 w-4" />
              How it works
            </Button>
            <Button loading={isScanning} onClick={handleScanNow}>
              <ScanSearch className="h-4 w-4" />
              Scan now
            </Button>
          </div>
        }
      />

      {error && (
        <div className="rounded-[24px] border border-red-500/15 bg-red-500/8 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <RadarVisual agents={filteredAgents} isScanning={isScanning} />
        <Card variant="glass">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">System scan orchestration</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Evidence-based host sweep</div>
            </div>
            <Badge variant="info" dot>
              {durationMs ? `${Math.round(durationMs)}ms` : 'Awaiting first run'}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Confirmed</div>
                <div className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-white">{agents.length}</div>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Running</div>
                <div className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-white">{runningCount}</div>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
                <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Connected</div>
                <div className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-white">{connectedCount}</div>
              </div>
            </div>

            <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">
                <ShieldCheck className="h-3.5 w-3.5" />
                What Nova sees
              </div>
              <p className="mt-3 max-w-[62ch] text-sm leading-7 text-nova-text-secondary">{summary}</p>
            </div>

            <ScanChecklist agents={agents} isScanning={isScanning} />

            <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">
                <BookOpen className="h-3.5 w-3.5" />
                Operator guidance
              </div>
              <p className="mt-3 max-w-[62ch] text-sm leading-7 text-nova-text-secondary">
                Discovery help documents supported runtimes, trust boundaries, and the production-safe n8n + Gmail anti-duplicate flow.
              </p>
              <div className="mt-4">
                <Button variant="outline" size="sm" onClick={() => navigate('/dashboard/help/discovery')}>
                  Open discovery help
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card variant="glass">
        <CardContent className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Filters</div>
            <div className="mt-2 text-sm text-nova-text-secondary">
              Discovery sorts by confidence first, then lets operators narrow by runtime class and live status.
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {typeOptions.map((option) => (
              <Button
                key={option.value}
                variant={typeFilter === option.value ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => setTypeFilter(option.value)}
              >
                {option.label}
              </Button>
            ))}
            {statusOptions.map((option) => (
              <Button
                key={option.value}
                variant={statusFilter === option.value ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter(option.value)}
              >
                {option.label}
              </Button>
            ))}
            {sortOptions.map((option) => (
              <Button
                key={option.value}
                variant={sortBy === option.value ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => setSortBy(option.value)}
              >
                Sort: {option.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {!isLoading && filteredAgents.length === 0 && !error ? (
        <EmptyState
          title="No real agents detected"
          description="Nova scanned the host and rejected weak matches. Install or start a supported runtime, then run the scan again."
          action={<Button onClick={handleScanNow}><SearchX className="h-4 w-4" /> Scan again</Button>}
        />
      ) : (
        <div className="grid gap-5 xl:grid-cols-3">
          {filteredAgents.map((agent) => (
            <DiscoveryCard
              key={agent.agent_key}
              agent={agent}
              isConnecting={connectingAgentKey === agent.agent_key}
              onConnect={() => handleConnect(agent.agent_key)}
              onManage={() => navigate('/agents')}
            />
          ))}
        </div>
      )}

      {connectedAgents.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Connected agents</div>
              <div className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">Live control surfaces</div>
            </div>
          </div>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {connectedAgents.map((agent) => (
              <motion.button
                key={agent.agent_key}
                whileHover={{ y: -2 }}
                onClick={() => navigate('/agents')}
                className="min-w-[320px] rounded-[28px] border border-white/10 bg-white/[0.03] p-5 text-left"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <AgentMark agent={agent} />
                    <div>
                      <div className="text-lg font-semibold text-white">{agent.name}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.18em] text-nova-text-secondary">{agent.type}</div>
                    </div>
                  </div>
                  <Badge variant="success" dot>Connected</Badge>
                </div>
                <div className="mt-5 flex items-end justify-between gap-4">
                  <SparkLine points={[18, 26, 22, 28, 34, 31, Math.max(12, Math.round((agent.confidence || 0.5) * 40))]} />
                  <div className="text-right">
                    <div className="text-sm text-nova-text-secondary">Confidence</div>
                    <div className="mt-1 text-2xl font-semibold text-white">{Math.round((agent.confidence || 0) * 100)}%</div>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default DiscoveryCenter

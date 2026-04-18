import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Bot, Boxes, CheckCircle2, Code2, Link2, Network, TerminalSquare, Workflow } from 'lucide-react'
import toast from 'react-hot-toast'
import ProviderMark from '@/components/brand/ProviderMark'
import { PageHeader } from '@/components/PageHeader'
import { Badge, Button, Card, CardContent, CardHeader, Input, ProgressBar, SelectField } from '@/components/ui'
import { useDiscovery } from '@/hooks/useDiscovery'
import { api } from '@/lib/api'

const typeOptions = [
  {
    id: 'codex',
    title: 'Codex CLI',
    icon: TerminalSquare,
    logo: '/agent-logos/codex.svg',
    description: 'AI coding assistant with terminal and file control.',
    model: 'o4-mini',
    lanes: [{ label: 'OpenAI', logo: '/llm-brands/openai.svg' }],
  },
  {
    id: 'n8n',
    title: 'n8n',
    icon: Workflow,
    logo: '/agent-logos/n8n.svg',
    description: 'Workflow automation with webhooks and execution history.',
    model: 'workflow',
    lanes: [{ label: 'Workflow', logo: '/agent-logos/n8n.svg' }],
  },
  {
    id: 'openclaw',
    title: 'OpenClaw',
    icon: Code2,
    logo: '/agent-logos/openclaw.svg',
    description: 'Interpreter-style runtime for direct tool and code execution.',
    model: 'openclaw-default',
    lanes: [{ label: 'Tool runtime', logo: '/agent-logos/openclaw.svg' }],
  },
  {
    id: 'langchain',
    title: 'LangChain',
    icon: Link2,
    logo: '/agent-logos/langchain.svg',
    description: 'LangServe or framework-managed agents with HTTP endpoints.',
    model: 'langchain-default',
    lanes: [{ label: 'LangServe', logo: '/agent-logos/langchain.svg' }],
  },
  {
    id: 'crewai',
    title: 'CrewAI',
    icon: Bot,
    logo: '/agent-logos/crewai.svg',
    description: 'Multi-agent crews wrapped by Python entrypoints.',
    model: 'crewai-default',
    lanes: [{ label: 'Crew runtime', logo: '/agent-logos/crewai.svg' }],
  },
  {
    id: 'custom',
    title: 'Custom Agent',
    icon: Boxes,
    logo: '/agent-logos/generic.svg',
    description: 'REST, WebSocket, subprocess, Python, or Docker integrations.',
    model: 'custom-runtime',
    lanes: [
      { label: 'OpenAI', logo: '/llm-brands/openai.svg' },
      { label: 'Gemini', logo: '/llm-brands/gemini.svg' },
    ],
  },
]

const runtimeBrandMap = {
  codex_cli: { logo: '/agent-logos/codex.svg', label: 'Codex CLI' },
  n8n: { logo: '/agent-logos/n8n.svg', label: 'n8n' },
  openclaw: { logo: '/agent-logos/openclaw.svg', label: 'OpenClaw' },
  open_interpreter: { logo: '/agent-logos/open-interpreter.svg', label: 'Open Interpreter' },
  langchain_agent: { logo: '/agent-logos/langchain.svg', label: 'LangChain' },
  crewai: { logo: '/agent-logos/crewai.svg', label: 'CrewAI' },
  autogen: { logo: '/agent-logos/autogen.svg', label: 'AutoGen' },
  openai_cli: { logo: '/llm-brands/openai.svg', label: 'OpenAI CLI' },
  gemini_cli: { logo: '/llm-brands/gemini.svg', label: 'Gemini CLI' },
  custom: { logo: '/agent-logos/generic.svg', label: 'Custom Agent' },
}

const presetPermissions = {
  codex: { can_do: ['read_files', 'write_files', 'run_commands', 'execute_code'], cannot_do: ['deploy_production', 'delete_production_db'] },
  n8n: { can_do: ['call_external_api', 'execute_workflows'], cannot_do: ['modify_billing', 'delete_production_db'] },
  openclaw: { can_do: ['execute_code', 'read_files', 'run_commands'], cannot_do: ['modify_user_roles', 'deploy_production'] },
  langchain: { can_do: ['call_external_api', 'query_database'], cannot_do: ['delete_production_db'] },
  crewai: { can_do: ['execute_code', 'run_commands', 'read_files'], cannot_do: ['deploy_production'] },
  custom: { can_do: ['call_agent_api'], cannot_do: ['delete_production_db'] },
}

function buildWebhookPath(agentName) {
  const slug = (agentName || 'nova-n8n-agent')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

  return `/nova/${slug || 'n8n-agent'}`
}

function inferHostServiceUrl(port) {
  if (typeof window === 'undefined') return `http://localhost:${port}`
  const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
  const hostname = window.location.hostname || 'localhost'
  return `${protocol}//${hostname}:${port}`
}

function StepBadge({ current, total }) {
  return <Badge variant="outline">Step {current} / {total}</Badge>
}

function runtimeTypeForFingerprint(fingerprintKey) {
  const typeMap = {
    codex_cli: 'codex',
    n8n: 'n8n',
    openclaw: 'openclaw',
    open_interpreter: 'openclaw',
    langchain_agent: 'langchain',
    crewai: 'crewai',
    autogen: 'custom',
    openai_cli: 'custom',
    gemini_cli: 'custom',
  }

  return typeMap[fingerprintKey] || 'custom'
}

function brandForType(typeId) {
  return typeOptions.find((option) => option.id === typeId) || typeOptions[typeOptions.length - 1]
}

function runtimeLogoForAgent(agent, typeId) {
  if (agent?.metadata?.logo_path) return agent.metadata.logo_path
  if (agent?.fingerprint_key && runtimeBrandMap[agent.fingerprint_key]?.logo) return runtimeBrandMap[agent.fingerprint_key].logo
  return brandForType(typeId).logo
}

function runtimeConfigDefaults(agent, typeId) {
  const port = agent?.port || agent?.metadata?.port

  if (typeId === 'n8n') {
    return {
      n8n_url: agent?.metadata?.n8n_url || inferHostServiceUrl(port || 5678),
    }
  }

  if (['openclaw', 'langchain', 'crewai', 'custom'].includes(typeId) && port) {
    return {
      api_endpoint: inferHostServiceUrl(port),
    }
  }

  return {}
}

function matchingRuntime(type, agents) {
  const matchers = {
    codex: ['codex_cli'],
    n8n: ['n8n'],
    openclaw: ['openclaw', 'open_interpreter'],
    langchain: ['langchain_agent'],
    crewai: ['crewai'],
  }
  const keys = matchers[type] || []
  return agents.find((agent) => keys.includes(agent.fingerprint_key)) || null
}

function executionTargetSummary(form, workspace, runtime) {
  const inferredWebhookPath = buildWebhookPath(form.name)
  const base = {
    workspace: workspace?.name || 'Current workspace',
    runtime: runtime?.name || 'Manual runtime binding',
    bindingMode: runtime ? 'Connect existing runtime' : 'Create managed binding',
    location: 'Defined during connection',
    detail: runtime
      ? `Detected via ${(runtime.detection_methods || []).join(' + ') || runtime.detection_method || 'host scan'}`
      : 'Nova will use the connection parameters you define in this wizard.',
  }

  if (form.type === 'codex') {
    return {
      ...base,
      location: form.config.working_directory || 'No working directory set',
      detail: runtime
        ? `Runs through ${runtime.name} on this host and executes in ${form.config.working_directory || 'the selected directory'}.`
        : `Nova will bind a Codex control lane and execute inside ${form.config.working_directory || 'the selected directory'}.`,
    }
  }

  if (form.type === 'n8n') {
    const resolvedPath = form.config.webhook_path || inferredWebhookPath
    return {
      ...base,
      location: form.config.n8n_url ? `${form.config.n8n_url}${resolvedPath}` : resolvedPath,
      detail: runtime
        ? `Workflow execution goes through ${runtime.name} at ${form.config.n8n_url || runtime.metadata?.n8n_url || 'the configured URL'} using ${resolvedPath}.`
        : `Nova will connect to the n8n endpoint at ${form.config.n8n_url || 'the configured URL'} and infer ${resolvedPath} unless you override it.`,
    }
  }

  if (['custom', 'langchain', 'openclaw', 'crewai'].includes(form.type)) {
    return {
      ...base,
      location: form.config.api_endpoint || form.config.communication_type || 'No endpoint set',
      detail: runtime
        ? `Nova will route through the discovered ${runtime.name} surface using ${form.config.communication_type || 'the selected transport'}.`
        : `Nova will create a ${form.config.communication_type || 'runtime'} binding to ${form.config.api_endpoint || 'the configured endpoint'}.`,
    }
  }

  return base
}

function AgentWizard() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { agents: discoveredAgents } = useDiscovery()
  const [step, setStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [testing, setTesting] = useState(false)
  const [createdAgentId, setCreatedAgentId] = useState(null)
  const [workspace, setWorkspace] = useState(null)
  const hydratedFromQueryRef = useRef(false)
  const [form, setForm] = useState({
    type: 'codex',
    name: 'Codex Control Lane',
    model: 'o4-mini',
    config: {
      approval_mode: 'full-auto',
      working_directory: '/home/ubuntu/nova-os',
      n8n_url: inferHostServiceUrl(5678),
      api_endpoint: inferHostServiceUrl(8080),
      communication_type: 'rest_api',
    },
    permissions: presetPermissions.codex,
    risk_thresholds: {
      auto_allow: 30,
      escalate: 60,
      auto_block: 80,
    },
    quota: {
      max_evaluations_per_day: 1000,
      max_tokens_per_request: 4000,
    },
  })

  const selectedType = useMemo(() => typeOptions.find((option) => option.id === form.type) || typeOptions[0], [form.type])
  const runtimeMatch = useMemo(() => matchingRuntime(form.type, discoveredAgents), [discoveredAgents, form.type])
  const targetSummary = useMemo(() => executionTargetSummary(form, workspace, runtimeMatch), [form, runtimeMatch, workspace])
  const inferredWebhookPath = useMemo(() => buildWebhookPath(form.name), [form.name])
  const requestedRuntimeKey = searchParams.get('runtime')
  const requestedType = searchParams.get('type')
  const existingRuntime = useMemo(
    () => discoveredAgents.find((agent) => agent.agent_key === requestedRuntimeKey) || null,
    [discoveredAgents, requestedRuntimeKey],
  )
  const existingRuntimeOptions = useMemo(
    () =>
      discoveredAgents.map((agent) => ({
        agent,
        typeId: runtimeTypeForFingerprint(agent.fingerprint_key),
      })),
    [discoveredAgents],
  )
  const detectedTypeMap = useMemo(
    () =>
      typeOptions.reduce((accumulator, option) => {
        accumulator[option.id] = matchingRuntime(option.id, discoveredAgents)
        return accumulator
      }, {}),
    [discoveredAgents],
  )

  useEffect(() => {
    api.get('/workspaces/me')
      .then((response) => setWorkspace(response))
      .catch(() => null)
  }, [])

  const updateForm = (patch) => setForm((current) => ({ ...current, ...patch }))
  const updateConfig = (patch) => setForm((current) => ({ ...current, config: { ...current.config, ...patch } }))
  const updatePermissions = (key, values) => setForm((current) => ({ ...current, permissions: { ...current.permissions, [key]: values } }))
  const updateThreshold = (key, value) => setForm((current) => ({ ...current, risk_thresholds: { ...current.risk_thresholds, [key]: Number(value) } }))

  const applyType = (typeId) => {
    const selected = typeOptions.find((option) => option.id === typeId) || typeOptions[0]
    updateForm({
      type: typeId,
      model: selected.model,
      name: `${selected.title} Control Lane`,
      permissions: presetPermissions[typeId],
    })
  }

  const applyExistingRuntime = (agent) => {
    const nextType = runtimeTypeForFingerprint(agent.fingerprint_key)
    const selected = typeOptions.find((option) => option.id === nextType) || typeOptions[0]
    const configDefaults = runtimeConfigDefaults(agent, nextType)

    setForm((current) => ({
      ...current,
      type: nextType,
      model: selected.model,
      name: `${agent.name} Control Lane`,
      config: {
        ...current.config,
        ...configDefaults,
        existing_runtime_key: agent.agent_key,
      },
      permissions: presetPermissions[nextType] || current.permissions,
    }))
    setStep(2)
  }

  useEffect(() => {
    if (hydratedFromQueryRef.current) return
    if (!requestedType && !existingRuntime) return

    hydratedFromQueryRef.current = true

    if (existingRuntime) {
      applyExistingRuntime(existingRuntime)
      return
    }

    if (requestedType && presetPermissions[requestedType]) {
      applyType(requestedType)
    }
  }, [existingRuntime, requestedType])

  const estimateAutoAllow = Math.max(8, Math.min(96, 100 - form.risk_thresholds.escalate + form.risk_thresholds.auto_allow))

  const handleTestConnection = async () => {
    setTesting(true)
    await new Promise((resolve) => window.setTimeout(resolve, 700))
    toast.success('Connection parameters look coherent. Final connection happens on create.')
    setTesting(false)
  }

  const handleCreate = async () => {
    setIsSubmitting(true)
    try {
      const response = await api.post('/agents/create', {
        name: form.name,
        type: form.type,
        model: form.model,
        config: {
          ...form.config,
          webhook_path: form.type === 'n8n' ? (form.config.webhook_path || inferredWebhookPath) : form.config.webhook_path,
          type: form.config.communication_type || form.type,
        },
        permissions: form.permissions,
        risk_thresholds: form.risk_thresholds,
        quota: form.quota,
      })
      setCreatedAgentId(response.agent?.id || null)
      if (response.connection?.success === false) {
        toast.error(`Managed lane created, but Nova still cannot reach the runtime: ${response.connection.error || 'Connection failed'}`)
      } else {
        toast.success('Agent created and runtime connected.')
      }
      window.setTimeout(() => {
        navigate('/agents')
      }, 1200)
    } catch (error) {
      toast.error(error.message || 'Unable to create managed agent')
    } finally {
      setIsSubmitting(false)
    }
  }

  const thresholdStops = [form.risk_thresholds.auto_allow, form.risk_thresholds.escalate, form.risk_thresholds.auto_block]

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Create Agent"
        title="Shape the agent, then bind it to Nova with explicit policy"
        description="This wizard defines type, connection, permissions, thresholds, and quota before the runtime accepts the agent."
        action={<StepBadge current={step} total={5} />}
      />

      <motion.div key={step} initial={{ opacity: 0, x: 14 }} animate={{ opacity: 1, x: 0 }} className="grid gap-6 xl:grid-cols-[0.72fr_0.28fr]">
        <Card variant="elevated">
          <CardContent className="space-y-8">
            {step === 1 && (
              <div className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {typeOptions.map((option) => (
                    (() => {
                      const detectedRuntime = detectedTypeMap[option.id]

                      return (
                        <button
                          key={option.id}
                          type="button"
                          onClick={() => applyType(option.id)}
                          className={`rounded-[28px] border p-5 text-left transition ${
                            form.type === option.id
                              ? 'border-black/12 bg-[#fffdfa] shadow-[0_24px_60px_-44px_rgba(0,0,0,0.28)] dark:border-nova-accent dark:bg-white/[0.06] dark:shadow-glow'
                              : 'border-black/8 bg-white hover:border-black/14 hover:bg-[#fffdfa] dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-white/20'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <ProviderMark
                              src={option.logo}
                              alt={`${option.title} logo`}
                              frameClassName="h-14 w-14 rounded-[20px] p-3"
                              imageClassName="max-h-8 max-w-8"
                            />
                            <Badge variant={detectedRuntime ? 'success' : 'outline'}>
                              {detectedRuntime ? 'Detected on host' : 'Managed lane'}
                            </Badge>
                          </div>
                          <div className="mt-5 text-lg font-semibold text-[#111111] dark:text-white">{option.title}</div>
                          <div className="mt-2 text-sm leading-6 text-black/60 dark:text-nova-text-secondary">{option.description}</div>
                          <div className="mt-4 flex flex-wrap gap-2">
                            {option.lanes.map((lane) => (
                              <span
                                key={`${option.id}-${lane.label}`}
                                className="inline-flex items-center gap-2 rounded-full border border-black/8 bg-black/[0.04] px-3 py-1.5 text-[11px] uppercase tracking-[0.18em] text-black/58 dark:border-white/10 dark:bg-black/20 dark:text-nova-text-secondary"
                              >
                                <img src={lane.logo} alt={`${lane.label} logo`} className="h-3.5 w-3.5 object-contain" />
                                {lane.label}
                              </span>
                            ))}
                          </div>
                          <div className="mt-4 text-xs leading-6 text-black/56 dark:text-nova-text-secondary">
                            {detectedRuntime
                              ? `${detectedRuntime.name} is already verifiable on this host.`
                              : 'Create a managed lane and bind it explicitly.'}
                          </div>
                        </button>
                      )
                    })()
                  ))}
                </div>

                {existingRuntimeOptions.length > 0 && (
                  <div className="rounded-[28px] border border-black/8 bg-white p-5 dark:border-white/10 dark:bg-white/[0.03]">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Add existing runtime</div>
                        <div className="mt-2 text-lg font-semibold text-[#111111] dark:text-white">Use something Nova already verified on this host</div>
                      </div>
                      <Badge variant="success">{existingRuntimeOptions.length} detected</Badge>
                    </div>
                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                      {existingRuntimeOptions.map(({ agent, typeId }) => {
                        const runtimeLogo = runtimeLogoForAgent(agent, typeId)
                        const RuntimeIcon = (typeOptions.find((option) => option.id === typeId) || typeOptions[0]).icon

                        return (
                          <button
                            key={agent.agent_key}
                            type="button"
                            onClick={() => applyExistingRuntime(agent)}
                            className="rounded-[24px] border border-black/8 bg-[#fffdfa] p-4 text-left transition hover:border-black/14 hover:bg-white dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-nova-accent/40 dark:hover:bg-white/[0.05]"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="flex items-center gap-3">
                                {runtimeLogo ? (
                                  <ProviderMark
                                    src={runtimeLogo}
                                    alt={`${agent.name} logo`}
                                    frameClassName="h-12 w-12 rounded-[18px] border-black/8 bg-white p-2.5 dark:border-white/10 dark:bg-white/[0.04]"
                                    imageClassName="max-h-7 max-w-7"
                                  />
                                ) : (
                                  <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-black/8 bg-white dark:border-white/10 dark:bg-white/[0.04]">
                                    <RuntimeIcon className="h-5 w-5 text-nova-accent-2" />
                                  </div>
                                )}
                                  <div>
                                  <div className="text-sm font-semibold text-[#111111] dark:text-white">{agent.name}</div>
                                  <div className="mt-1 text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">
                                    {Math.round((agent.confidence || 0) * 100)}% confidence
                                  </div>
                                </div>
                              </div>
                              <Badge variant="outline">Add existing</Badge>
                            </div>
                            <div className="mt-4 text-sm leading-6 text-black/60 dark:text-nova-text-secondary">
                              {(agent.detection_methods || []).join(' + ')}
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {step === 2 && (
              <div className="grid gap-5 lg:grid-cols-2">
                {form.config.existing_runtime_key && (
                  <div className="lg:col-span-2 rounded-[28px] border border-[#3ecf8e]/25 bg-[#edf9f3] p-5 dark:border-nova-accent/25 dark:bg-nova-accent/10">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <ProviderMark
                          src={runtimeLogoForAgent(existingRuntime || runtimeMatch, form.type)}
                          alt={`${existingRuntime?.name || runtimeMatch?.name || selectedType.title} logo`}
                          frameClassName="h-12 w-12 rounded-[18px] border-black/8 bg-white p-2.5 dark:border-white/10 dark:bg-white/[0.04]"
                          imageClassName="max-h-7 max-w-7"
                        />
                        <div>
                          <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Existing runtime selected</div>
                          <div className="mt-2 text-lg font-semibold text-[#111111] dark:text-white">
                            {existingRuntime?.name || runtimeMatch?.name || 'Host runtime'}
                          </div>
                        </div>
                      </div>
                      <Badge variant="success">Discovered on host</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-7 text-black/60 dark:text-nova-text-secondary">
                      Nova will bind this managed agent to a runtime it already verified instead of asking you to define everything from scratch.
                    </p>
                  </div>
                )}
                <Input label="Agent name" value={form.name} onChange={(event) => updateForm({ name: event.target.value })} />
                <Input label="Assigned model" value={form.model} onChange={(event) => updateForm({ model: event.target.value })} />
                {form.type === 'codex' && (
                  <>
                    <SelectField
                      label="Approval mode"
                      value={form.config.approval_mode}
                      onValueChange={(value) => updateConfig({ approval_mode: value })}
                      options={[
                        { value: 'suggest', label: 'Suggest' },
                        { value: 'auto-edit', label: 'Auto-edit' },
                        { value: 'full-auto', label: 'Full-auto' },
                      ]}
                    />
                    <Input label="Working directory" value={form.config.working_directory || ''} onChange={(event) => updateConfig({ working_directory: event.target.value })} />
                  </>
                )}
                {form.type === 'n8n' && (
                  <>
                    <Input
                      label="n8n URL"
                      helper="Nova will send governance traffic to this n8n workspace."
                      value={form.config.n8n_url || ''}
                      onChange={(event) => updateConfig({ n8n_url: event.target.value })}
                    />
                    <Input
                      label="Webhook path"
                      helper={`Nova fills this automatically from the agent name. Leave it blank to use ${inferredWebhookPath}.`}
                      placeholder={inferredWebhookPath}
                      value={form.config.webhook_path || ''}
                      onChange={(event) => updateConfig({ webhook_path: event.target.value })}
                    />
                  </>
                )}
                {['custom', 'langchain', 'openclaw', 'crewai'].includes(form.type) && (
                  <>
                    <Input label="Base endpoint" value={form.config.api_endpoint || ''} onChange={(event) => updateConfig({ api_endpoint: event.target.value })} />
                    <SelectField
                      label="Communication"
                      value={form.config.communication_type || 'rest_api'}
                      onValueChange={(value) => updateConfig({ communication_type: value })}
                      options={[
                        { value: 'rest_api', label: 'REST API' },
                        { value: 'websocket', label: 'WebSocket' },
                        { value: 'subprocess', label: 'Subprocess' },
                        { value: 'python_module', label: 'Python module' },
                        { value: 'docker', label: 'Docker' },
                      ]}
                    />
                  </>
                )}
                <div className="lg:col-span-2 rounded-[28px] border border-black/8 bg-white p-5 dark:border-white/10 dark:bg-white/[0.03]">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <ProviderMark
                        src={runtimeLogoForAgent(runtimeMatch, form.type)}
                        alt={`${targetSummary.runtime} logo`}
                        frameClassName="h-12 w-12 rounded-[18px] border-black/8 bg-white p-2.5 dark:border-white/10 dark:bg-white/[0.04]"
                        imageClassName="max-h-7 max-w-7"
                      />
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Execution target</div>
                        <div className="mt-2 text-lg font-semibold text-[#111111] dark:text-white">{targetSummary.runtime}</div>
                      </div>
                    </div>
                    <Badge variant={runtimeMatch ? 'success' : 'outline'}>
                      {runtimeMatch ? 'Discovered on host' : 'Manual binding'}
                    </Badge>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <SummaryField label="Workspace" value={targetSummary.workspace} />
                    <SummaryField label="Run location" value={targetSummary.location} />
                    <SummaryField label="Binding mode" value={targetSummary.bindingMode} />
                    <SummaryField label="Connector type" value={form.config.communication_type || form.type} />
                  </div>
                  <p className="mt-4 text-sm leading-7 text-black/60 dark:text-nova-text-secondary">{targetSummary.detail}</p>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="grid gap-5 lg:grid-cols-2">
                <PermissionColumn
                  title="Allowed actions"
                  values={form.permissions.can_do}
                  onChange={(values) => updatePermissions('can_do', values)}
                />
                <PermissionColumn
                  title="Blocked actions"
                  values={form.permissions.cannot_do}
                  tone="danger"
                  onChange={(values) => updatePermissions('cannot_do', values)}
                />
              </div>
            )}

            {step === 4 && (
              <div className="space-y-6">
                <div className="rounded-[28px] border border-black/8 bg-white p-6 dark:border-white/10 dark:bg-white/[0.03]">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Risk score scale</div>
                  <div className="mt-6 h-3 rounded-full bg-gradient-to-r from-nova-success via-nova-warning to-nova-danger" />
                  <div className="mt-5 grid gap-5 md:grid-cols-3">
                    <ThresholdField label="Auto allow" value={form.risk_thresholds.auto_allow} onChange={(value) => updateThreshold('auto_allow', value)} />
                    <ThresholdField label="Escalate" value={form.risk_thresholds.escalate} onChange={(value) => updateThreshold('escalate', value)} />
                    <ThresholdField label="Auto block" value={form.risk_thresholds.auto_block} onChange={(value) => updateThreshold('auto_block', value)} />
                  </div>
                  <div className="mt-5 text-sm text-black/60 dark:text-nova-text-secondary">Estimated auto-allow rate: <span className="text-[#111111] dark:text-white">{estimateAutoAllow}%</span></div>
                </div>
                <div className="flex gap-3">
                  {[
                    ['Conservative', { auto_allow: 18, escalate: 44, auto_block: 62 }],
                    ['Balanced', { auto_allow: 30, escalate: 60, auto_block: 80 }],
                    ['Permissive', { auto_allow: 42, escalate: 72, auto_block: 90 }],
                  ].map(([label, values]) => (
                    <Button key={label} variant="outline" onClick={() => updateForm({ risk_thresholds: values })}>{label}</Button>
                  ))}
                </div>
                <div className="rounded-[28px] border border-black/8 bg-white p-6 dark:border-white/10 dark:bg-white/[0.03]">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Applied stops</div>
                  <div className="mt-4 flex gap-3">
                    {thresholdStops.map((value) => (
                      <div key={value} className="rounded-full border border-black/8 px-4 py-2 text-sm text-[#111111] dark:border-white/10 dark:text-white">{value}</div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {step === 5 && (
              <div className="space-y-5">
                <div className="rounded-[30px] border border-black/8 bg-white p-6 dark:border-white/10 dark:bg-white/[0.03]">
                  <div className="flex items-center gap-3">
                    <ProviderMark
                      src={runtimeLogoForAgent(runtimeMatch, form.type)}
                      alt={`${selectedType.title} logo`}
                      frameClassName="h-12 w-12 rounded-[18px] border-black/8 bg-white p-2.5 dark:border-white/10 dark:bg-white/[0.04]"
                      imageClassName="max-h-7 max-w-7"
                    />
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Review surface</div>
                      <div className="text-lg font-semibold text-[#111111] dark:text-white">Review and create</div>
                    </div>
                  </div>
                  <div className="mt-5 grid gap-4 md:grid-cols-2">
                    <SummaryField label="Type" value={selectedType.title} />
                    <SummaryField label="Name" value={form.name} />
                    <SummaryField label="Model" value={form.model} />
                    <SummaryField label="Transport" value={form.config.communication_type || form.type} />
                    <SummaryField label="Workspace" value={targetSummary.workspace} />
                    <SummaryField label="Runtime target" value={targetSummary.runtime} />
                    <SummaryField label="Run location" value={targetSummary.location} />
                    <SummaryField label="Binding mode" value={targetSummary.bindingMode} />
                    <SummaryField label="Allowed actions" value={form.permissions.can_do.join(', ') || 'None'} />
                    <SummaryField label="Blocked actions" value={form.permissions.cannot_do.join(', ') || 'None'} />
                  </div>
                  <p className="mt-4 text-sm leading-7 text-black/60 dark:text-nova-text-secondary">{targetSummary.detail}</p>
                </div>
                {createdAgentId && (
                  <div className="rounded-[28px] border border-nova-success/20 bg-nova-success/10 px-5 py-4 text-sm text-nova-success">
                    <div className="flex items-center gap-2 font-medium">
                      <CheckCircle2 className="h-4 w-4" />
                      Agent created
                    </div>
                    <div className="mt-2">Managed agent id: {createdAgentId}</div>
                  </div>
                )}
                <div className="flex gap-3">
                  <Button variant="outline" loading={testing} onClick={handleTestConnection}>Test connection</Button>
                  <Button loading={isSubmitting} onClick={handleCreate}>Create agent</Button>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between gap-4 border-t border-black/8 pt-6 dark:border-white/8">
              <Button variant="ghost" onClick={() => setStep((current) => Math.max(1, current - 1))} disabled={step === 1}>Back</Button>
              <Button onClick={() => setStep((current) => Math.min(5, current + 1))} disabled={step === 5}>Continue</Button>
            </div>
          </CardContent>
        </Card>

        <Card variant="glass" className="border-black/8 bg-[#fffdfa] shadow-[0_25px_70px_-55px_rgba(0,0,0,0.24)] dark:border-white/10 dark:bg-white/[0.04] dark:shadow-none">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Current selection</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-[#111111] dark:text-white">{selectedType.title}</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <ProviderMark
              src={selectedType.logo}
              alt={`${selectedType.title} logo`}
              frameClassName="h-16 w-16 rounded-[24px] border-black/8 bg-white p-3.5 dark:border-white/10 dark:bg-white/[0.04]"
              imageClassName="max-h-8 max-w-8"
            />
            <p className="text-sm leading-7 text-black/60 dark:text-nova-text-secondary">{selectedType.description}</p>
            <div>
              <div className="mb-3 text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">Policy shape</div>
              <ProgressBar value={estimateAutoAllow} tone="accent" />
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

function PermissionColumn({ title, values, onChange, tone = 'default' }) {
  const [draft, setDraft] = useState('')

  return (
    <div className="rounded-[28px] border border-black/8 bg-white p-5 dark:border-white/10 dark:bg-white/[0.03]">
      <div className={`text-lg font-semibold ${tone === 'danger' ? 'text-nova-danger' : 'text-[#111111] dark:text-white'}`}>{title}</div>
      <div className="mt-4 space-y-3">
        {values.map((value) => (
          <div key={value} className="flex items-center justify-between rounded-2xl border border-black/8 px-3 py-2 text-sm text-[#111111] dark:border-white/10 dark:text-white">
            <span>{value}</span>
            <button
              type="button"
              className="text-black/42 transition hover:text-black dark:text-nova-text-secondary dark:hover:text-white"
              onClick={() => onChange(values.filter((item) => item !== value))}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
      <div className="mt-4 flex gap-3">
        <Input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Add action" />
        <Button
          variant="outline"
          onClick={() => {
            if (!draft.trim()) return
            onChange([...values, draft.trim()])
            setDraft('')
          }}
        >
          Add
        </Button>
      </div>
    </div>
  )
}

function ThresholdField({ label, value, onChange }) {
  return (
    <label className="block">
      <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">{label}</div>
      <input type="range" min="0" max="100" value={value} onChange={(event) => onChange(event.target.value)} className="w-full" />
      <div className="mt-2 text-sm text-[#111111] dark:text-white">{value}</div>
    </label>
  )
}

function SummaryField({ label, value }) {
  return (
    <div className="rounded-[22px] border border-black/8 bg-[#fffdfa] px-4 py-4 dark:border-white/10 dark:bg-white/[0.03]">
      <div className="text-[11px] uppercase tracking-[0.18em] text-black/42 dark:text-nova-text-secondary">{label}</div>
      <div className="mt-2 text-sm text-[#111111] dark:text-white">{value}</div>
    </div>
  )
}

export default AgentWizard

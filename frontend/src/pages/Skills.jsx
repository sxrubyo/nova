import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BrainCircuit, ExternalLink, Github, MailWarning, Plus, ScanSearch, Search, ShieldCheck, Wrench } from 'lucide-react'
import { api } from '../utils/api'
import ProviderMark from '@/components/brand/ProviderMark'

const connectorBrandMap = {
  airtable: { name: 'Airtable', logo: '/brands/airtable.svg', tone: 'bg-white' },
  datadog: { name: 'Datadog', logo: '/brands/datadog.svg', tone: 'bg-white' },
  discord: { name: 'Discord', logo: '/brands/discord.svg', tone: 'bg-white' },
  github: { name: 'GitHub', logo: '/brands/github.svg', tone: 'bg-white' },
  gmail: { name: 'Gmail', logo: '/brands/gmail.svg', tone: 'bg-white' },
  hubspot: { name: 'HubSpot', logo: '/brands/hubspot.svg', tone: 'bg-white' },
  jira: { name: 'Jira', logo: '/brands/jira.svg', tone: 'bg-white' },
  linear: { name: 'Linear', logo: '/brands/linear.svg', tone: 'bg-white' },
  make: { name: 'Make', logo: '/brands/make.svg', tone: 'bg-white' },
  notion: { name: 'Notion', logo: '/brands/notion.svg', tone: 'bg-white' },
  pagerduty: { name: 'PagerDuty', logo: '/brands/pagerduty.svg', tone: 'bg-white' },
  postgres: { name: 'PostgreSQL', logo: '/brands/postgresql.svg', tone: 'bg-white' },
  redis: { name: 'Redis', logo: '/brands/redis.svg', tone: 'bg-white' },
  salesforce: { name: 'Salesforce', tone: 'bg-[#eaf6ff]' },
  slack: { name: 'Slack', logo: '/brands/slack.svg', tone: 'bg-white' },
  stripe: { name: 'Stripe', logo: '/brands/stripe.svg', tone: 'bg-white' },
  supabase: { name: 'Supabase', logo: '/brands/supabase.svg', tone: 'bg-white' },
  telegram: { name: 'Telegram', logo: '/brands/telegram.svg', tone: 'bg-white' },
  webhook: { name: 'Webhook', tone: 'bg-[#f6f1e6]' },
  whatsapp: { name: 'WhatsApp', logo: '/brands/whatsapp.svg', tone: 'bg-white' },
  zapier: { name: 'Zapier', logo: '/brands/zapier.svg', tone: 'bg-white' },
}

const categoryMap = {
  slack: 'Communication',
  gmail: 'Communication',
  telegram: 'Communication',
  whatsapp: 'Communication',
  discord: 'Communication',
  hubspot: 'Business',
  salesforce: 'Business',
  stripe: 'Business',
  airtable: 'Data',
  notion: 'Data',
  postgres: 'Data',
  redis: 'Data',
  supabase: 'Developer',
  github: 'Developer',
  jira: 'Developer',
  linear: 'Developer',
  webhook: 'Developer',
  make: 'Developer',
  zapier: 'Developer',
  datadog: 'Other',
  pagerduty: 'Other',
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
}

const githubRecommendations = [
  {
    name: 'security-best-practices',
    description: 'Checklist and review workflow for shipping a security product without weak defaults.',
    url: 'https://github.com/openai/skills/tree/main/skills/.curated/security-best-practices',
    category: 'Security',
  },
  {
    name: 'security-threat-model',
    description: 'Threat-modeling workflow to validate auth, data flow and operational risk before shipping changes.',
    url: 'https://github.com/openai/skills/tree/main/skills/.curated/security-threat-model',
    category: 'Security',
  },
  {
    name: 'playwright-interactive',
    description: 'Browser-driven testing and visual validation for production UI flows.',
    url: 'https://github.com/openai/skills/tree/main/skills/.curated/playwright-interactive',
    category: 'Frontend QA',
  },
  {
    name: 'figma-implement-design',
    description: 'Production implementation workflow for taking serious design files into code cleanly.',
    url: 'https://github.com/openai/skills/tree/main/skills/.curated/figma-implement-design',
    category: 'Design',
  },
]

const categoryOrder = ['Communication', 'Business', 'Data', 'Developer', 'Other']

const runtimeTypeMap = {
  codex_cli: 'codex',
  n8n: 'n8n',
  openclaw: 'openclaw',
  open_interpreter: 'openclaw',
  langchain_agent: 'langchain',
  crewai: 'crewai',
  autogen: 'custom',
}

function Skills() {
  const navigate = useNavigate()
  const [skills, setSkills] = useState([])
  const [gatewayProviders, setGatewayProviders] = useState([])
  const [existingRuntimes, setExistingRuntimes] = useState([])
  const [connectorSummary, setConnectorSummary] = useState({ catalog_count: 0, connected_count: 0, incomplete_count: 0 })
  const [searchQuery, setSearchQuery] = useState('')
  const [loadError, setLoadError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  const loadSkills = useCallback(async () => {
    setLoadError('')
    try {
      const [skillData, modelData, discoveryData, connectorData] = await Promise.all([
        api.get('/skills'),
        api.get('/assistant/models').catch(() => ({ providers: [] })),
        api.get('/discovery/agents').catch(() => ({ agents: [] })),
        api.get('/connectors').catch(() => ({ connectors: [], summary: {} })),
      ])

      const registryByKey = Object.fromEntries(
        (connectorData.connectors || []).map((connector) => [connector.key, connector]),
      )

      const normalized = Object.entries(skillData || {}).map(([key, value]) => {
        const registry = registryByKey[key] || {}

        return {
          id: key,
          key,
          name: connectorBrandMap[key]?.name || value?.name || key,
          category: categoryMap[key] || value?.category || 'Other',
          description: value?.description || 'No description provided',
          fields: Object.keys(value?.credentials || value?.schema || {}).length,
          logo: connectorBrandMap[key]?.logo || null,
          tone: connectorBrandMap[key]?.tone || 'bg-[#111111]',
          capabilities: registry.capabilities || value?.capabilities || [],
          setupUrl: registry.setup_url || value?.setup_url || null,
          connected: Boolean(registry.connected),
          status: registry.status || 'available',
          connectedVia: registry.connected_via || null,
          configuredFields: registry.configured_fields || [],
          requiredFields: registry.required_fields || [],
        }
      })

      setSkills(normalized)
      setGatewayProviders(modelData.providers || [])
      setExistingRuntimes(
        [...(discoveryData.agents || [])].sort((left, right) => (right.confidence || 0) - (left.confidence || 0)),
      )
      setConnectorSummary({
        catalog_count: connectorData.summary?.catalog_count || normalized.length,
        connected_count: connectorData.summary?.connected_count || 0,
        incomplete_count: connectorData.summary?.incomplete_count || 0,
      })
    } catch (err) {
      setLoadError(err.message || 'Failed to load skills')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSkills()
  }, [loadSkills])

  const filteredSkills = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) return skills
    return skills.filter((skill) => {
      const haystack = `${skill.name} ${skill.category} ${skill.description} ${skill.capabilities.join(' ')}`.toLowerCase()
      return haystack.includes(query)
    })
  }, [skills, searchQuery])

  const groupedSkills = useMemo(() => {
    return categoryOrder
      .map((category) => ({
        category,
        items: filteredSkills.filter((skill) => skill.category === category),
      }))
      .filter((group) => group.items.length > 0)
  }, [filteredSkills])

  const addExistingRuntime = (runtime) => {
    const type = runtimeTypeMap[runtime.fingerprint_key] || 'custom'
    navigate(`/dashboard/agents/new?type=${encodeURIComponent(type)}&runtime=${encodeURIComponent(runtime.agent_key)}`)
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
      <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-[#fffdfa] p-7 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Integrations and skills</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-[#111111] dark:text-white">Capabilities attached to Nova</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-black/62 dark:text-white/62">
          Real runtime connectors, model gateways, and developer-side capabilities are grouped here so the product stays clear even as Nova grows.
        </p>
      </motion.section>

      {loadError && (
        <motion.div variants={item} className="rounded-[24px] border border-red-500/15 bg-red-500/8 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {loadError}
        </motion.div>
      )}

      <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Gateway and model lane</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Available LLM providers</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-black/58 dark:text-white/58">
              These are the real gateways Nova can use right now from your environment. Users can choose them directly from the operator panel.
            </p>
          </div>
          <BrainCircuit className="mt-1 h-5 w-5 text-black/35 dark:text-white/35" />
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {gatewayProviders.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-black/10 bg-[#fbf7ef] p-5 text-sm text-black/48 dark:border-white/[0.06] dark:bg-white/[0.03] dark:text-white/48 md:col-span-2 xl:col-span-4">
              No LLM providers are configured yet. Add keys in `.env` and Nova will expose them automatically.
            </div>
          ) : (
            gatewayProviders.map((provider) => (
              <div key={provider.key} className="rounded-[26px] border border-black/8 bg-[#fffdfa] p-5 shadow-[0_24px_55px_-45px_rgba(0,0,0,0.25)] dark:border-transparent dark:bg-white/[0.03] dark:shadow-[0_28px_70px_-48px_rgba(0,0,0,0.82)]">
                <div className="flex items-start justify-between gap-3">
                  <ProviderMark
                    src={provider.logo}
                    alt={`${provider.label} logo`}
                    frameClassName="h-12 w-12 rounded-[18px] p-2.5"
                    imageClassName="max-h-6 max-w-6"
                  />
                  <span className="rounded-full bg-[#3ecf8e]/12 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#1e8a5c]">
                    {provider.available ? 'Server key' : 'Use your key'}
                  </span>
                </div>
                <h3 className="mt-5 text-lg font-semibold text-[#111111] dark:text-white">{provider.label}</h3>
                <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">{provider.description}</p>
                <div className="mt-5 flex items-center justify-between border-t border-black/8 pt-4 text-xs text-black/46 dark:border-white/[0.06] dark:text-white/46">
                  <span>{provider.models.length} models</span>
                  <span>{provider.models.find((model) => model.id === provider.default_model)?.label || provider.default_model}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </motion.section>

      <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Existing runtimes</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Add something Nova already found</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-black/58 dark:text-white/58">
              This closes one of the gaps versus the CLI: you can now jump straight from a verified host runtime into the add-agent flow with its logo and detection evidence already attached.
            </p>
          </div>
          <button
            onClick={() => navigate('/dashboard/discover')}
            className="inline-flex items-center gap-2 rounded-2xl border border-black/10 bg-white px-5 py-3 text-sm font-semibold text-[#111111] transition hover:border-black/20 dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-white"
          >
            <ScanSearch className="h-4 w-4" />
            Open discovery
          </button>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {existingRuntimes.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-black/10 bg-[#fbf7ef] p-5 text-sm text-black/48 dark:border-white/[0.06] dark:bg-white/[0.03] dark:text-white/48 md:col-span-2 xl:col-span-3">
              No verified host runtimes are available in this session yet. Run a Discovery scan first, then return here to add them with the correct runtime identity.
            </div>
          ) : (
            existingRuntimes.map((runtime) => (
              <div key={runtime.agent_key} className="rounded-[26px] border border-black/8 bg-[#fffdfa] p-5 shadow-[0_24px_55px_-45px_rgba(0,0,0,0.25)] dark:border-transparent dark:bg-white/[0.03] dark:shadow-[0_28px_70px_-48px_rgba(0,0,0,0.82)]">
                <div className="flex items-start justify-between gap-3">
                  {runtime.metadata?.logo_path ? (
                    <ProviderMark
                      src={runtime.metadata.logo_path}
                      alt={`${runtime.name} logo`}
                      frameClassName="h-12 w-12 rounded-[18px] p-2.5"
                      imageClassName="max-h-6 max-w-6"
                    />
                  ) : (
                    <div className="flex h-12 w-12 items-center justify-center rounded-[18px] bg-[#111111] text-white dark:bg-white/10">
                      <Wrench className="h-4 w-4" />
                    </div>
                  )}
                  <span className="rounded-full bg-[#3ecf8e]/12 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#1e8a5c]">
                    {Math.round((runtime.confidence || 0) * 100)}% confidence
                  </span>
                </div>
                <h3 className="mt-5 text-lg font-semibold text-[#111111] dark:text-white">{runtime.name}</h3>
                <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">
                  {(runtime.detection_methods || []).join(' + ')} · {(runtime.metadata?.matched_signals || runtime.detection_methods?.length || 0)} verified signals
                </p>
                <div className="mt-5 flex gap-3">
                  <button
                    onClick={() => addExistingRuntime(runtime)}
                    className="inline-flex items-center gap-2 rounded-2xl bg-[#111111] px-4 py-3 text-sm font-semibold text-white transition hover:bg-black dark:bg-white dark:text-[#111111]"
                  >
                    <Plus className="h-4 w-4" />
                    Add existing
                  </button>
                  <button
                    onClick={() => navigate('/dashboard/discover')}
                    className="inline-flex items-center gap-2 rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm font-semibold text-[#111111] transition hover:border-black/20 dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-white"
                  >
                    Review evidence
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </motion.section>

      <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-white p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Backend integrations</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Available runtime connectors</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-black/58 dark:text-white/58">
              Common connectors stay obvious. Infrastructure and harder-to-explain tools are grouped lower under Developer and Other.
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-black/40 dark:text-white/40">
              {connectorSummary.connected_count} connected · {connectorSummary.incomplete_count} incomplete · {connectorSummary.catalog_count} in catalog
            </p>
          </div>
          <div className="relative w-full max-w-xl">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/32 dark:text-white/32" />
            <input
              type="text"
              placeholder="Search connectors, gateways, or MCPs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-2xl border border-black/8 bg-[#f6f1e6] py-3 pl-11 pr-4 text-sm text-[#111111] outline-none transition focus:border-black/14 focus:bg-white dark:border-white/[0.07] dark:bg-white/[0.04] dark:text-white dark:placeholder:text-white/30 dark:focus:border-white/14 dark:focus:bg-white/[0.06]"
            />
          </div>
        </div>

        <div className="mt-6 space-y-7">
          {isLoading ? (
            <div className="rounded-[24px] border border-dashed border-black/10 bg-[#fbf7ef] p-5 text-sm text-black/48 dark:border-white/[0.06] dark:bg-white/[0.03] dark:text-white/48">
              Loading integrations...
            </div>
          ) : groupedSkills.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-black/10 bg-[#fbf7ef] p-5 text-sm text-black/48 dark:border-white/[0.06] dark:bg-white/[0.03] dark:text-white/48">
              No integrations match the current search.
            </div>
          ) : (
            groupedSkills.map((group) => (
              <div key={group.category}>
                <div className="mb-4 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">{group.category}</p>
                    <p className="mt-1 text-sm text-black/52 dark:text-white/52">{group.items.length} connectors</p>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {group.items.map((skill) => (
                    <div key={skill.id} className="rounded-[26px] border border-black/8 bg-[#fffdfa] p-5 shadow-[0_24px_55px_-45px_rgba(0,0,0,0.25)] dark:border-transparent dark:bg-white/[0.03] dark:shadow-[0_28px_70px_-48px_rgba(0,0,0,0.82)]">
                      <div className="flex items-start justify-between gap-3">
                        <div className={`flex h-12 w-12 items-center justify-center rounded-[18px] ${skill.logo ? `${skill.tone} shadow-[0_18px_40px_-30px_rgba(0,0,0,0.22)]` : 'bg-[#111111] text-white dark:bg-white/10 dark:text-white'}`}>
                          {skill.logo ? (
                            <img src={skill.logo} alt={`${skill.name} logo`} className="h-7 w-7 object-contain" />
                          ) : skill.key === 'salesforce' ? (
                            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#009adb]">SF</span>
                          ) : skill.key === 'webhook' ? (
                            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-black/70 dark:text-white/70">WEB</span>
                          ) : (
                            <Wrench className="h-4 w-4" />
                          )}
                        </div>
                        <span
                          className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
                            skill.connected
                              ? 'bg-[#3ecf8e]/12 text-[#1e8a5c]'
                              : skill.status === 'incomplete'
                                ? 'bg-[#d59f2a]/12 text-[#a87410]'
                                : 'bg-black/6 text-black/50 dark:bg-white/[0.06] dark:text-white/52'
                          }`}
                        >
                          {skill.connected ? 'Connected via CLI' : skill.status === 'incomplete' ? 'Incomplete setup' : 'Available'}
                        </span>
                      </div>
                      <h3 className="mt-5 text-lg font-semibold text-[#111111] dark:text-white">{skill.name}</h3>
                      <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">{skill.description}</p>
                      <p className="mt-3 text-xs leading-6 text-black/48 dark:text-white/48">
                        {skill.connected
                          ? `${skill.configuredFields.length} configured field${skill.configuredFields.length === 1 ? '' : 's'} detected in the local Nova skill store.`
                          : skill.status === 'incomplete'
                            ? `Credential file found, but ${Math.max(skill.requiredFields.length - skill.configuredFields.length, 1)} required field${Math.max(skill.requiredFields.length - skill.configuredFields.length, 1) === 1 ? '' : 's'} still need values.`
                            : 'No local connector credentials detected yet.'}
                      </p>
                      <div className="mt-5 flex items-center justify-between border-t border-black/8 pt-4 text-xs text-black/46 dark:border-white/[0.06] dark:text-white/46">
                        <span>{skill.category}</span>
                        <span>{skill.capabilities.length || skill.fields} capabilities</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </motion.section>

      <motion.section variants={item} className="rounded-[30px] border border-[#d59f2a]/20 bg-[#fffaf0] p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.15)] dark:border-[#d59f2a]/20 dark:bg-[#1b1812] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[18px] bg-[#d59f2a]/12 text-[#a87410]">
            <MailWarning className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Gmail duplicate guard</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">What the anti-duplicate check actually validates today</h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-black/62 dark:text-white/62">
              Nova currently checks duplicate emails against its own ledger of governed `send_email` actions. That means it can reliably block repeats that already passed through Nova, but it does not automatically read your full Gmail Sent mailbox unless you wire a Gmail API/OAuth sync for that purpose.
            </p>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-black/62 dark:text-white/62">
              For n8n, the safe pattern is still: Nova duplicate check before send, Gmail send, then Nova evaluation/ledger write after approval. If you want cross-checking against historical messages already in Gmail, that is a separate integration step and should be surfaced as Gmail mailbox sync, not implied as if it already exists.
            </p>
          </div>
        </div>
      </motion.section>

      <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-[#11151b] p-6 text-white shadow-[0_25px_70px_-55px_rgba(0,0,0,0.55)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-white/42">GitHub recommendations</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Skills worth using for Nova</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-white/64">
              These are the GitHub-hosted skills that make the most sense for a security product frontend and delivery workflow.
            </p>
          </div>
          <Github className="mt-1 h-5 w-5 text-white/40" />
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {githubRecommendations.map((skill) => (
            <a
              key={skill.name}
              href={skill.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-[24px] border border-white/10 bg-white/6 p-5 transition hover:border-white/18 hover:bg-white/9"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-white/8 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/62">
                  {skill.category}
                </span>
                <ExternalLink className="h-4 w-4 text-white/42" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-white">{skill.name}</h3>
              <p className="mt-2 text-sm leading-6 text-white/66">{skill.description}</p>
            </a>
          ))}
        </div>

        <div className="mt-6 rounded-[24px] border border-white/10 bg-white/6 p-4 text-sm text-white/72">
          <div className="flex items-center gap-2 font-semibold">
            <ShieldCheck className="h-4 w-4 text-[#79d9ab]" />
            Installed for this workspace
          </div>
          <p className="mt-2 leading-6 text-white/64">
            `security-best-practices`, `security-threat-model` and `playwright-interactive` were installed locally to support this cleanup and future frontend validation work.
          </p>
        </div>
      </motion.section>
    </motion.div>
  )
}

export default Skills

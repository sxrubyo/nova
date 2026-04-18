import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { BrainCircuit, ExternalLink, Github, Search, ShieldCheck, Wrench } from 'lucide-react'
import { api } from '../utils/api'

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

function Skills() {
  const [skills, setSkills] = useState([])
  const [gatewayProviders, setGatewayProviders] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loadError, setLoadError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  const loadSkills = useCallback(async () => {
    setLoadError('')
    try {
      const [skillData, modelData] = await Promise.all([
        api.get('/skills'),
        api.get('/assistant/models').catch(() => ({ providers: [] })),
      ])

      const normalized = Object.entries(skillData || {}).map(([key, value]) => ({
        id: key,
        key,
        name: connectorBrandMap[key]?.name || value?.name || key,
        category: categoryMap[key] || value?.category || 'Other',
        description: value?.description || 'No description provided',
        fields: Object.keys(value?.credentials || value?.schema || {}).length,
        logo: connectorBrandMap[key]?.logo || null,
        tone: connectorBrandMap[key]?.tone || 'bg-[#111111]',
      }))

      setSkills(normalized)
      setGatewayProviders(modelData.providers || [])
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
      const haystack = `${skill.name} ${skill.category} ${skill.description}`.toLowerCase()
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
                  <div className="flex h-12 w-12 items-center justify-center rounded-[18px] bg-white shadow-[0_18px_40px_-30px_rgba(0,0,0,0.22)]">
                    <img src={provider.logo} alt={`${provider.label} logo`} className="h-7 w-7 object-contain" />
                  </div>
                  <span className="rounded-full bg-[#3ecf8e]/12 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#1e8a5c]">
                    Live
                  </span>
                </div>
                <h3 className="mt-5 text-lg font-semibold text-[#111111] dark:text-white">{provider.label}</h3>
                <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">{provider.description}</p>
                <div className="mt-5 flex items-center justify-between border-t border-black/8 pt-4 text-xs text-black/46 dark:border-white/[0.06] dark:text-white/46">
                  <span>{provider.models.length} models</span>
                  <span>{provider.default_model}</span>
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
                        <span className="rounded-full bg-[#3ecf8e]/12 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#1e8a5c]">
                          Ready
                        </span>
                      </div>
                      <h3 className="mt-5 text-lg font-semibold text-[#111111] dark:text-white">{skill.name}</h3>
                      <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">{skill.description}</p>
                      <div className="mt-5 flex items-center justify-between border-t border-black/8 pt-4 text-xs text-black/46 dark:border-white/[0.06] dark:text-white/46">
                        <span>{skill.category}</span>
                        <span>{skill.fields} auth fields</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
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

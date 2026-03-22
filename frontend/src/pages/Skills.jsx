import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { ExternalLink, Github, Search, ShieldCheck, Wrench } from 'lucide-react'
import { api } from '../utils/api'

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

function Skills() {
  const [skills, setSkills] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loadError, setLoadError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  const loadSkills = useCallback(async () => {
    setLoadError('')
    try {
      const data = await api.get('/skills')
      const normalized = Object.entries(data || {}).map(([key, value]) => ({
        id: key,
        key,
        name: value?.name || key,
        category: value?.category || 'Integration',
        description: value?.description || 'No description provided',
        fields: Object.keys(value?.credentials || value?.schema || {}).length,
      }))
      setSkills(normalized)
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

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
      <motion.section variants={item} className="rounded-[30px] border border-black/8 bg-[#fffdfa] p-7 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] dark:border-transparent dark:bg-[#151a1f] dark:shadow-[0_32px_80px_-52px_rgba(0,0,0,0.82)]">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Integrations and skills</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-[#111111] dark:text-white">Capabilities attached to Nova</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-black/62 dark:text-white/62">
          This page now separates real backend integrations from curated GitHub skills that help build, secure and validate the product.
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
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/42 dark:text-white/42">Backend integrations</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">Available runtime connectors</h2>
          </div>
          <div className="relative w-full max-w-xl">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/32 dark:text-white/32" />
            <input
              type="text"
              placeholder="Search connectors and MCPs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-2xl border border-black/8 bg-[#f6f1e6] py-3 pl-11 pr-4 text-sm text-[#111111] outline-none transition focus:border-black/14 focus:bg-white dark:border-white/[0.07] dark:bg-white/[0.04] dark:text-white dark:placeholder:text-white/30 dark:focus:border-white/14 dark:focus:bg-white/[0.06]"
            />
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {isLoading ? (
            <div className="rounded-[24px] border border-dashed border-black/10 bg-[#fbf7ef] p-5 text-sm text-black/48 dark:border-white/[0.06] dark:bg-white/[0.03] dark:text-white/48 md:col-span-2 xl:col-span-3">
              Loading integrations...
            </div>
          ) : filteredSkills.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-black/10 bg-[#fbf7ef] p-5 text-sm text-black/48 dark:border-white/[0.06] dark:bg-white/[0.03] dark:text-white/48 md:col-span-2 xl:col-span-3">
              No integrations match the current search.
            </div>
          ) : (
            filteredSkills.map((skill) => (
              <div key={skill.id} className="rounded-[24px] border border-black/8 bg-[#fffdfa] p-5 dark:border-transparent dark:bg-white/[0.03]">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#111111] text-white">
                    <Wrench className="h-4 w-4" />
                  </div>
                  <span className="rounded-full bg-[#3ecf8e]/12 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#1e8a5c]">
                    Live
                  </span>
                </div>
                <h3 className="mt-5 text-lg font-semibold text-[#111111] dark:text-white">{skill.name}</h3>
                <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">{skill.description}</p>
                <div className="mt-5 flex items-center justify-between border-t border-black/8 pt-4 text-xs text-black/46 dark:border-white/[0.06] dark:text-white/46">
                  <span>{skill.category}</span>
                  <span>{skill.fields} auth fields</span>
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

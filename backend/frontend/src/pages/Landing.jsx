import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Eye,
  Fingerprint,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Waves,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useTheme } from '../context/ThemeContext'

const novaIsotipoBlack = new URL('../../nova-branding/Nova I/Black Nova Isotipo.png', import.meta.url).href
const novaIsotipoWhite = new URL('../../nova-branding/Nova I/White Nova Isotipo.png', import.meta.url).href
const dashboardPreview = '/images/novad.png'

const heroSignals = [
  {
    title: 'Watch every action',
    description: 'See what an agent tried to do, why it was approved, and where risk appeared.',
  },
  {
    title: 'Intervene before impact',
    description: 'Approve, block, or escalate risky behavior before it reaches customers or infrastructure.',
  },
  {
    title: 'Keep evidence by default',
    description: 'Every critical decision lands in a ledger with score, timing, and reason.',
  },
]

const operatorStories = [
  {
    eyebrow: 'Observe',
    title: 'One runtime view for alerts, decisions, timelines, and model activity.',
    description:
      'Operators should not have to assemble context from five tools. Nova brings queue, ledger, live events, and model access into one place.',
    icon: Eye,
    accent: 'Live operator context',
  },
  {
    eyebrow: 'Decide',
    title: 'A human-readable control layer for what agents can do next.',
    description:
      'Teams can review policy outcomes, inspect risk, and decide quickly whether an action should continue, stop, or escalate.',
    icon: ShieldCheck,
    accent: 'Approvals with context',
  },
  {
    eyebrow: 'Prove',
    title: 'Every important action stays traceable after the moment has passed.',
    description:
      'When somebody asks what happened, Nova can show the event, the verdict, the score, and the surrounding evidence without guesswork.',
    icon: Fingerprint,
    accent: 'Evidence built in',
  },
]

const workflowSteps = [
  {
    step: '01',
    title: 'Connect the agent you already have',
    description:
      'Wrap an existing service or agent runtime without rebuilding your whole stack around governance first.',
  },
  {
    step: '02',
    title: 'Choose how the operator works',
    description:
      'Use the dashboard, the CLI, or the assistant panel to inspect models, run checks, and control actions in plain language.',
  },
  {
    step: '03',
    title: 'Review outcomes with confidence',
    description:
      'Alerts, approvals, blocks, and streaming events stay visible enough that non-developers can still follow what is going on.',
  },
]

const proofStats = [
  { value: '1 surface', label: 'for runtime, alerts, ledger, and models' },
  { value: '<200ms', label: 'target validation latency for governed actions' },
  { value: '24/7', label: 'operator visibility into live decisions' },
  { value: 'full trace', label: 'from prompt to policy outcome when needed' },
]

const commandRows = [
  'nova connect --url http://localhost:8001 --name support-agent',
  'nova protect --upstream http://localhost:8001 --agent support-agent',
  'nova alerts',
  'nova stream --agent support-agent',
]

const revealFromDark = {
  hidden: {
    opacity: 0,
    y: 42,
    filter: 'blur(18px)',
  },
  show: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: 0.85,
      ease: [0.16, 1, 0.3, 1],
    },
  },
}

function Landing() {
  const { theme } = useTheme()
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isDark = theme === 'dark'
  const themeClasses = isDark
    ? {
        page: 'bg-[#0a0e12] text-white',
        hero: 'bg-[radial-gradient(circle_at_12%_12%,rgba(62,207,142,0.14),transparent_24%),radial-gradient(circle_at_88%_12%,rgba(93,124,255,0.16),transparent_26%),linear-gradient(180deg,#0a0e12_0%,#10161c_54%,#11161d_100%)]',
        section: 'bg-[#0d1217]',
        sectionAlt: 'bg-[#070b10]',
        line: 'border-white/10',
        card: 'border-white/[0.07] bg-white/[0.035]',
        softCard: 'border-white/[0.06] bg-white/[0.03]',
        heroCard: 'border-white/[0.08] bg-[#11171d]/85',
        panel: 'border-white/[0.08] bg-[#121821]',
        subtle: 'text-white/66',
        subtleStrong: 'text-white/76',
        input: 'border-white/12 bg-white/[0.06] text-white placeholder:text-white/34',
        secondaryButton: 'border-white/12 bg-white/[0.05] text-white hover:bg-white/[0.08]',
        iso: novaIsotipoWhite,
      }
    : {
        page: 'bg-[#f4efe5] text-[#111111]',
        hero: 'bg-[radial-gradient(circle_at_10%_12%,rgba(62,207,142,0.12),transparent_26%),radial-gradient(circle_at_88%_8%,rgba(93,124,255,0.12),transparent_26%),linear-gradient(180deg,#f8f3ea_0%,#f4efe5_55%,#ece6da_100%)]',
        section: 'bg-[#f7f2e8]',
        sectionAlt: 'bg-[#efe8db]',
        line: 'border-black/8',
        card: 'border-black/8 bg-white/80',
        softCard: 'border-black/8 bg-[#fffdfa]',
        heroCard: 'border-black/8 bg-white/88',
        panel: 'border-black/8 bg-white',
        subtle: 'text-black/60',
        subtleStrong: 'text-black/74',
        input: 'border-black/10 bg-white text-[#111111] placeholder:text-black/34',
        secondaryButton: 'border-black/10 bg-white/80 text-[#111111] hover:bg-white',
        iso: novaIsotipoBlack,
      }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    await new Promise((resolve) => setTimeout(resolve, 900))
    setIsSubmitting(false)
    setEmail('')
  }

  return (
    <div className={`min-h-screen overflow-hidden ${themeClasses.page}`}>
      <div className={`relative ${themeClasses.hero}`}>
        <div className="absolute inset-x-0 top-0 h-px bg-white/8 dark:bg-white/8" />
        <div className="absolute left-[-8%] top-[-4%] h-[420px] w-[420px] rounded-full bg-[#3ecf8e]/12 blur-3xl" />
        <div className="absolute right-[-12%] top-8 h-[540px] w-[540px] rounded-full bg-[#6d84ff]/10 blur-3xl" />
        <div className="absolute left-[22%] top-[46%] h-[260px] w-[260px] rounded-full bg-white/[0.03] blur-3xl" />

        <nav className="relative z-10">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <div className={`flex h-14 w-14 items-center justify-center rounded-2xl border ${themeClasses.card}`}>
                <img src={themeClasses.iso} alt="Nova isotipo" className="h-11 w-11 object-contain" />
              </div>
              <div>
                <p className="text-base font-semibold tracking-[-0.03em]">Nova</p>
                <p className={`text-xs ${themeClasses.subtle}`}>Govern what your agents can do in production.</p>
              </div>
            </div>

            <div className="hidden items-center gap-8 md:flex">
              <a href="#workflow" className={`text-sm font-medium transition ${themeClasses.subtle} hover:text-current`}>How it works</a>
              <a href="#operators" className={`text-sm font-medium transition ${themeClasses.subtle} hover:text-current`}>For operators</a>
              <a href="#cli" className={`text-sm font-medium transition ${themeClasses.subtle} hover:text-current`}>CLI</a>
              <Link
                to="/login"
                className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#111111] transition hover:bg-[#f1f1f1]"
              >
                Open Nova
              </Link>
            </div>
          </div>
        </nav>

        <section className="relative z-10 mx-auto grid min-h-[calc(100vh-88px)] max-w-7xl gap-12 px-4 pb-20 pt-8 sm:px-6 lg:grid-cols-[0.86fr_1.14fr] lg:items-center lg:px-8 lg:pb-24">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#3ecf8e]/22 bg-[#3ecf8e]/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#72d8aa]">
              <Sparkles className="h-3.5 w-3.5" />
              Agent governance for real operations
            </div>

            <h1 className="mt-7 max-w-4xl text-[clamp(3.7rem,9vw,8.5rem)] font-semibold leading-[0.88] tracking-[-0.065em]">
              See what your agents are doing before they create consequences.
            </h1>

            <p className={`mt-6 max-w-2xl text-lg leading-8 ${themeClasses.subtleStrong}`}>
              Nova turns agent governance into something operators can actually use: understand the action, review the risk, choose the outcome, and keep the evidence.
            </p>

            <div className="mt-9 flex flex-col gap-4 sm:flex-row">
              <Link
                to="/login"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-7 py-4 text-sm font-semibold text-[#111111] transition hover:bg-[#f1f1f1]"
              >
                Launch operator console
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="#workflow"
                className={`inline-flex items-center justify-center rounded-full border px-7 py-4 text-sm font-semibold transition ${themeClasses.secondaryButton}`}
              >
                Understand the flow
              </a>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {heroSignals.map((signal) => (
                <div
                  key={signal.title}
                  className={`rounded-[28px] border p-5 shadow-[0_30px_70px_-55px_rgba(0,0,0,0.45)] ${themeClasses.softCard}`}
                >
                  <p className="text-lg font-semibold tracking-[-0.03em]">{signal.title}</p>
                  <p className={`mt-3 text-sm leading-6 ${themeClasses.subtle}`}>{signal.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative min-h-[640px] overflow-visible lg:min-h-[840px]">
            <div className="absolute right-4 top-0 z-20 w-full max-w-[360px] rounded-[30px] border border-white/10 bg-[#121822]/78 p-5 text-white shadow-[0_32px_90px_-62px_rgba(0,0,0,0.9)] backdrop-blur-xl dark:bg-[#121822]/78 lg:right-10">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-white/50">Operator brief</p>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">One surface for runtime, models, and evidence.</h2>
              <div className="mt-5 space-y-3">
                <BriefRow label="Talk with your agent" value="Choose provider, model, and API key" />
                <BriefRow label="Operator queue" value="Review alerts without switching tools" />
                <BriefRow label="Ledger" value="Keep a trace of every critical decision" />
              </div>
            </div>

            <DesktopMock isDark={isDark} />
          </div>
        </section>
      </div>

      <motion.section
        id="workflow"
        variants={revealFromDark}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.24 }}
        className={`py-24 ${themeClasses.section}`}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <p className={`text-[11px] font-mono uppercase tracking-[0.22em] ${themeClasses.subtle}`}>How Nova works</p>
            <h2 className="mt-4 text-[clamp(2.8rem,5vw,5rem)] font-semibold leading-[0.96] tracking-[-0.05em]">
              The product should feel understandable before the first incident happens.
            </h2>
            <p className={`mt-5 max-w-2xl text-base leading-8 ${themeClasses.subtleStrong}`}>
              Nova is strongest when the operator can answer three questions fast: what happened, what matters now, and what should we do next.
            </p>
          </div>

          <div className="mt-12 grid gap-5 lg:grid-cols-3">
            {workflowSteps.map((step) => (
              <div
                key={step.step}
                className={`rounded-[30px] border p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] ${themeClasses.card}`}
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#3ecf8e]">{step.step}</p>
                <h3 className="mt-5 text-2xl font-semibold tracking-[-0.04em]">{step.title}</h3>
                <p className={`mt-4 text-sm leading-7 ${themeClasses.subtle}`}>{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </motion.section>

      <section id="operators" className={`py-24 ${themeClasses.sectionAlt}`}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-[0.92fr_1.08fr] lg:items-start">
            <div>
              <p className={`text-[11px] font-mono uppercase tracking-[0.22em] ${themeClasses.subtle}`}>For operators</p>
              <h2 className="mt-4 text-[clamp(2.8rem,5vw,4.8rem)] font-semibold leading-[0.98] tracking-[-0.05em]">
                Nova should explain itself even if you are not deep in the codebase.
              </h2>
              <p className={`mt-5 max-w-xl text-base leading-8 ${themeClasses.subtleStrong}`}>
                The dashboard needs to communicate decisions in human terms. That means clearer alerts, clearer model access, and a clearer path from question to action.
              </p>
            </div>

            <div className="grid gap-5">
              {operatorStories.map((story) => (
                <OperatorStoryCard key={story.title} story={story} isDark={isDark} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <motion.section
        variants={revealFromDark}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.24 }}
        className="bg-[#06090d] py-24 text-white"
      >
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-[36px] border border-white/10 bg-white/[0.04] px-6 py-12 backdrop-blur-xl sm:px-10 lg:px-12">
            <p className="text-center text-[11px] font-mono uppercase tracking-[0.22em] text-white/42">Why teams keep it open</p>
            <div className="mt-12 grid gap-px overflow-hidden rounded-[26px] border border-white/8 bg-white/8 sm:grid-cols-2 xl:grid-cols-4">
              {proofStats.map((item) => (
                <div key={item.label} className="flex min-h-[180px] flex-col items-center justify-center bg-[#06090d] px-6 py-8 text-center">
                  <p className="text-[clamp(2.4rem,3.2vw,3.6rem)] font-semibold leading-none tracking-[-0.05em]">{item.value}</p>
                  <p className="mt-4 max-w-[16ch] text-[10px] uppercase leading-6 tracking-[0.18em] text-white/50">{item.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.section>

      <motion.section
        id="cli"
        variants={revealFromDark}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.24 }}
        className={`py-24 ${themeClasses.section}`}
      >
        <div className="mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[0.84fr_1.16fr] lg:items-center lg:px-8">
          <div>
            <p className={`text-[11px] font-mono uppercase tracking-[0.22em] ${themeClasses.subtle}`}>CLI surface</p>
            <h2 className="mt-4 text-[clamp(2.8rem,5vw,4.8rem)] font-semibold leading-[0.98] tracking-[-0.05em]">
              Use Nova from the terminal without losing visibility or operator control.
            </h2>
            <p className={`mt-5 max-w-xl text-base leading-8 ${themeClasses.subtleStrong}`}>
              The CLI is not a side path. It is part of the same governed system, so operators can connect services, inspect alerts, and stream events without creating a second workflow.
            </p>
          </div>

          <div className="overflow-hidden rounded-[32px] border border-white/10 bg-[#0d131a] text-white shadow-[0_35px_90px_-55px_rgba(0,0,0,0.75)]">
            <div className="flex items-center gap-2 border-b border-white/8 px-5 py-4">
              <span className="h-2.5 w-2.5 rounded-full bg-white/25" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/25" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/25" />
              <span className="ml-3 text-xs uppercase tracking-[0.24em] text-white/48">operator shell</span>
            </div>
            <div className="space-y-3 px-5 py-5 font-mono text-sm leading-7 text-white">
              {commandRows.map((row) => (
                <div key={row} className="flex gap-3">
                  <span className="text-[#79d9ab]">$</span>
                  <span>{row}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.section>

      <section className="bg-[#05070a] py-24 text-white">
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8">
          <div className="mx-auto flex h-14 w-14 items-center justify-center">
            <img src={novaIsotipoWhite} alt="Nova isotipo" className="h-12 w-12 object-contain" />
          </div>
          <h2 className="mt-6 text-4xl font-semibold tracking-[-0.04em]">
            Start governing agent behavior before it reaches production.
          </h2>
          <p className="mt-4 text-base leading-7 text-white/68">
            Request access for your workspace and start reviewing live actions, policy decisions, model choices, and runtime evidence in one place.
          </p>

          <form onSubmit={handleSubmit} className="mx-auto mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row">
            <input
              type="email"
              placeholder="operator@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={`min-w-0 flex-1 rounded-full border px-5 py-4 outline-none transition ${themeClasses.input}`}
            />
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-full bg-white px-7 py-4 text-sm font-semibold text-[#111111] transition hover:bg-[#f3f3f3] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? 'Sending...' : 'Request access'}
            </button>
          </form>
        </div>
      </section>
    </div>
  )
}

function DesktopMock({ isDark }) {
  return (
    <div className="relative h-full w-full overflow-visible">
      <motion.div
        initial={{
          opacity: 0,
          x: 240,
          scale: 0.94,
          rotate: -0.8,
          rotateY: -14,
          filter: 'blur(24px)',
        }}
        animate={{
          opacity: 1,
          x: 0,
          scale: 1,
          rotate: -2.2,
          rotateY: 0,
          filter: 'blur(0px)',
        }}
        transition={{
          duration: 2,
          delay: 0.24,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="absolute left-[4%] top-16 w-[152%] [transform-style:preserve-3d] lg:left-[14%] lg:top-10 lg:w-[168%]"
      >
        <div className={`absolute inset-x-[10%] bottom-[-52px] h-28 rounded-full blur-3xl ${isDark ? 'bg-[#3ecf8e]/18' : 'bg-[#95d8b4]/38'}`} />
        <div className="relative overflow-hidden rounded-[34px] border border-white/[0.07] bg-[#11161b] p-3 shadow-[0_90px_220px_-95px_rgba(0,0,0,0.85)]">
          <img
            src={dashboardPreview}
            alt="Nova dashboard screenshot"
            className="block h-auto w-full rounded-[26px] object-cover"
          />
        </div>
      </motion.div>
    </div>
  )
}

function BriefRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3">
      <p className="text-sm font-medium text-white/72">{label}</p>
      <p className="max-w-[13ch] text-right text-sm font-semibold text-white">{value}</p>
    </div>
  )
}

function OperatorStoryCard({ story, isDark }) {
  const Icon = story.icon

  return (
    <div
      className={`rounded-[30px] border p-6 shadow-[0_25px_70px_-55px_rgba(0,0,0,0.35)] ${isDark ? 'border-white/[0.08] bg-white/[0.04]' : 'border-black/8 bg-white/82'}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${isDark ? 'text-white/42' : 'text-black/42'}`}>{story.eyebrow}</p>
          <h3 className={`mt-4 text-2xl font-semibold tracking-[-0.04em] ${isDark ? 'text-white' : 'text-[#111111]'}`}>{story.title}</h3>
        </div>
        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${isDark ? 'bg-white/[0.05]' : 'bg-black/[0.04]'}`}>
          <Icon className={`h-5 w-5 ${isDark ? 'text-white/78' : 'text-[#111111]'}`} />
        </div>
      </div>
      <p className={`mt-4 text-sm leading-7 ${isDark ? 'text-white/66' : 'text-black/60'}`}>{story.description}</p>
      <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-[#3ecf8e]/18 bg-[#3ecf8e]/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#69d1a2]">
        {story.accent === 'Live operator context' ? <Waves className="h-3.5 w-3.5" /> : story.accent === 'Approvals with context' ? <ShieldCheck className="h-3.5 w-3.5" /> : <TerminalSquare className="h-3.5 w-3.5" />}
        {story.accent}
      </div>
    </div>
  )
}

export default Landing

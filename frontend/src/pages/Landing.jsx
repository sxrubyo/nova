import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ShieldCheck, Waves, TerminalSquare } from 'lucide-react'
import { motion } from 'framer-motion'
import { SERVER_IP } from '../config/appConfig'
import { useTheme } from '../context/ThemeContext'

const novaIsotipoBlack = new URL('../../nova-branding/Nova I/Black Nova Isotipo.png', import.meta.url).href
const novaIsotipoWhite = new URL('../../nova-branding/Nova I/White Nova Isotipo.png', import.meta.url).href
const dashboardPreview = '/images/novad.png'

const heroSignals = [
  { value: '/validate', label: 'review policies before an agent can act' },
  { value: '/stream/events', label: 'watch decisions and incidents live' },
  { value: 'ledger', label: 'keep evidence for every critical action' },
]

const scrollSections = [
  {
    id: 'control',
    align: 'left',
    eyebrow: '01  Runtime Control',
    title: 'Every action is reviewed before it touches customers, data, or infrastructure.',
    description:
      'Put approvals, policy checks, and evidence in front of production actions. Nova helps teams stop unsafe behavior before it becomes a customer, data, or infra problem.',
    accent: 'validate',
  },
  {
    id: 'operators',
    align: 'right',
    eyebrow: '02  Operator Surface',
    title: 'Operators see risk, queue, and timeline without switching tools.',
    description:
      'Security, platform, and operations teams get one place to review alerts, inspect decisions, follow live events, and understand why an agent was blocked or approved.',
    accent: 'alerts',
  },
  {
    id: 'ship',
    align: 'left',
    eyebrow: '03  Deployment Reality',
    title: 'Connect existing agents without rebuilding the stack around them.',
    description:
      'Bring current services behind Nova with controlled access, policy enforcement, and rollout visibility. You keep your stack and gain a safer operating layer.',
    accent: 'connect',
  },
]

const stats = [
  { value: '99.94%', label: 'decision trace availability' },
  { value: '<200ms', label: 'median validation latency' },
  { value: '24/7', label: 'operator visibility' },
  { value: '2 yrs', label: 'market momentum' },
]

const commandRows = [
  'nova connect --url http://localhost:8001 --name sales-guard',
  'nova protect --upstream http://localhost:8001 --agent sales-guard',
  'nova alerts',
  'nova stream --agent sales-guard',
]

const revealFromDark = {
  hidden: {
    opacity: 0,
    y: 46,
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
        page: 'bg-[#0b0e11] text-white',
        grid: 'bg-[radial-gradient(circle_at_top_left,rgba(62,207,142,0.08),transparent_30%),linear-gradient(180deg,#0b0e11_0%,#11161b_52%,#151a1f_100%)]',
        subtle: 'text-white/62',
        subtleStrong: 'text-white/74',
        line: 'border-white/10',
        section: 'bg-[#13181d]',
        card: 'bg-white/[0.035] border-white/[0.06]',
        cardSoft: 'bg-white/[0.03] border-white/[0.05]',
        panel: 'bg-[#171c22] border-white/[0.06]',
        input: 'bg-white/[0.06] border-white/12 text-white placeholder:text-white/36',
        buttonAlt: 'border-white/12 bg-white/[0.05] text-white hover:bg-white/[0.09]',
        marquee: 'text-white/[0.03] [text-shadow:0_0_1px_rgba(255,255,255,0.08)]',
        iso: novaIsotipoWhite,
      }
    : {
        page: 'bg-[#f3ede2] text-[#111111]',
        grid: 'bg-[radial-gradient(circle_at_top_left,rgba(62,207,142,0.10),transparent_32%),radial-gradient(circle_at_82%_12%,rgba(81,119,255,0.10),transparent_28%),linear-gradient(180deg,#f7f1e7_0%,#f3ede2_58%,#ece5d8_100%)]',
        subtle: 'text-black/62',
        subtleStrong: 'text-black/72',
        line: 'border-black/8',
        section: 'bg-[#f7f2e8]',
        card: 'bg-white/80 border-black/8',
        cardSoft: 'bg-[#fffdfa] border-black/8',
        panel: 'bg-white border-black/8',
        input: 'bg-white border-black/10 text-[#111111] placeholder:text-black/32',
        buttonAlt: 'border-black/10 bg-white/80 text-[#111111] hover:bg-white',
        marquee: 'text-black/[0.035] [text-shadow:0_0_1px_rgba(17,17,17,0.08)]',
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
      <div className={`relative ${themeClasses.grid}`}>
        <div className="pointer-events-none absolute inset-x-0 top-0 z-0 h-[280px] bg-[linear-gradient(180deg,rgba(0,0,0,0.42)_0%,rgba(0,0,0,0.18)_42%,transparent_100%)] blur-2xl" />
        <div className="absolute inset-x-0 top-0 h-px bg-white/8 dark:bg-white/8" />
        <div className="absolute left-0 top-20 h-[420px] w-[420px] rounded-full bg-[#3ecf8e]/8 blur-3xl" />
        <div className="absolute right-0 top-16 h-[520px] w-[520px] rounded-full bg-white/[0.04] blur-3xl" />

        <nav className="relative z-10">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3">
              <div className={`flex h-14 w-14 items-center justify-center rounded-2xl border ${themeClasses.line} ${themeClasses.card}`}>
                <img src={themeClasses.iso} alt="Nova isotipo" className="h-11 w-11 object-contain" />
              </div>
	              <div>
	                <p className="text-base font-semibold">Secure What Acts <span className={themeClasses.subtle}>| Nova</span></p>
	              </div>
            </div>

            <div className="hidden items-center gap-8 md:flex">
              <a href="#runtime" className={`text-sm font-medium transition ${themeClasses.subtle} hover:text-current`}>Runtime</a>
              <a href="#stats" className={`text-sm font-medium transition ${themeClasses.subtle} hover:text-current`}>Stats</a>
              <a href="#cli" className={`text-sm font-medium transition ${themeClasses.subtle} hover:text-current`}>CLI</a>
              <Link to="/login" className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#111111] transition hover:bg-[#f3f3f3]">
                Open console
              </Link>
            </div>
          </div>
        </nav>

        <section className="relative z-10 mx-auto grid min-h-[calc(100vh-88px)] max-w-7xl gap-12 px-4 pb-20 pt-8 sm:px-6 lg:grid-cols-[0.88fr_1.12fr] lg:items-center lg:px-8 lg:pb-24">
	          <div>
            <h1 className="max-w-4xl text-[clamp(4rem,10vw,9.5rem)] font-semibold uppercase leading-[0.9] tracking-[-0.06em]">
              Control
              <br />
              live agent
              <br />
              actions.
            </h1>
            <p className={`mt-6 max-w-2xl text-lg leading-8 ${themeClasses.subtleStrong}`}>
              Nova gives operators a control layer for AI systems in production: review actions, trace decisions, monitor risk, and respond before customers or infrastructure are exposed.
            </p>

            <div className="mt-9 flex flex-col gap-4 sm:flex-row">
              <Link to="/login" className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-7 py-4 text-sm font-semibold text-[#111111] transition hover:bg-[#f3f3f3]">
                Launch dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#runtime" className={`inline-flex items-center justify-center rounded-full border px-7 py-4 text-sm font-semibold transition ${themeClasses.buttonAlt}`}>
                Explore runtime surface
              </a>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {heroSignals.map((signal) => (
                <div key={signal.value} className={`rounded-[26px] border p-5 shadow-[0_30px_70px_-55px_rgba(0,0,0,0.55)] ${themeClasses.cardSoft}`}>
                  <p className="text-2xl font-semibold tracking-[-0.03em]">{signal.value}</p>
                  <p className={`mt-2 text-sm leading-6 ${themeClasses.subtle}`}>{signal.label}</p>
                </div>
              ))}
            </div>
          </div>

		          <div className="relative min-h-[620px] overflow-visible lg:min-h-[860px]">
		            <div className="absolute left-[14%] top-[16%] h-[320px] w-[320px] rounded-full bg-[#3ecf8e]/10 blur-3xl lg:left-[28%] lg:h-[460px] lg:w-[460px]" />
		            <div className="absolute right-[-2%] top-[20%] h-[240px] w-[240px] rounded-full bg-white/[0.04] blur-3xl lg:right-[-6%] lg:h-[340px] lg:w-[340px]" />
		            <DesktopMock />
	          </div>
        </section>
      </div>

      <section id="runtime" className={`relative py-24 ${isDark ? 'bg-[#090d12]' : 'bg-[#f7f2e8]'}`}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="space-y-24">
            {scrollSections.map((section, index) => (
              <motion.div
                key={section.id}
                variants={revealFromDark}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true, amount: 0.28 }}
                className={`grid gap-8 lg:grid-cols-2 lg:items-center ${section.align === 'right' ? 'lg:[&>*:first-child]:order-2 lg:[&>*:last-child]:order-1' : ''}`}
              >
                <div className={section.align === 'left' ? 'lg:pr-[12%]' : 'lg:pl-[12%]'}>
                  <p className={`text-[11px] font-mono uppercase tracking-[0.22em] ${themeClasses.subtle}`}>{section.eyebrow}</p>
                  <h2 className="mt-4 text-[clamp(2.6rem,5vw,4.8rem)] font-semibold leading-[0.98] tracking-[-0.05em]">
                    {index === 0 ? (
                      <>
	                        Every <span className="font-semibold text-[#3ecf8e] [text-shadow:0_0_22px_rgba(62,207,142,0.18)]">action</span> is reviewed before it touches customers, data, or infrastructure.
                      </>
                    ) : (
                      section.title
                    )}
                  </h2>
                  <p className={`mt-5 max-w-xl text-base leading-8 ${themeClasses.subtleStrong}`}>
                    {section.description}
                  </p>
                  <div className="mt-8 inline-flex items-center gap-2 rounded-full border border-[#3ecf8e]/18 bg-[#3ecf8e]/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#79d9ab]">
                    {index === 0 ? <ShieldCheck className="h-3.5 w-3.5" /> : index === 1 ? <Waves className="h-3.5 w-3.5" /> : <TerminalSquare className="h-3.5 w-3.5" />}
                    {section.accent}
                  </div>
                </div>

                <div className={`rounded-[32px] border p-6 shadow-[0_35px_90px_-55px_rgba(0,0,0,0.55)] ${themeClasses.panel}`}>
                  <div className={`grid gap-4 ${index === 1 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
                    <DataCard
                      title={index === 0 ? 'Validation layer' : index === 1 ? 'Alert queue' : 'CLI bridge'}
                      value={index === 0 ? 'APPROVED / BLOCKED / ESCALATED' : index === 1 ? '12 active items' : 'protect / connect'}
                      copy={index === 0 ? 'Score, reason, risk, evidence and response are treated as one decision event.' : index === 1 ? 'Teams see what needs review without guessing where the failure happened.' : 'Operators can wrap existing HTTP agents and govern them without rewriting application logic.'}
                      isDark={isDark}
                    />
                    <DataCard
                      title={index === 0 ? 'Immutable ledger' : index === 1 ? 'Risk profile' : 'Agent creation'}
                      value={index === 0 ? 'chain verified' : index === 1 ? '3 agents on watch' : 'natural-language token'}
                      copy={index === 0 ? 'Every governed action enters the audit trail with verdict, score, and timing metadata.' : index === 1 ? 'Risk scoring surfaces unstable or noisy agents before they become incidents.' : 'Describe an operational role and Nova generates a governed token with permissions and restrictions.'}
                      isDark={isDark}
                    />
                    {index === 1 && (
                      <DataCard
                        title="Live stream"
                        value="SSE connected"
                        copy="Validation decisions, anomalies, and alerts land in one runtime feed."
                        isDark={isDark}
                      />
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <motion.section
        id="stats"
        variants={revealFromDark}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.22 }}
        className="bg-[#05070a] py-24 text-white"
      >
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
			          <div className="rounded-[34px] border border-white/10 bg-black/45 px-6 py-12 backdrop-blur-xl sm:px-10 lg:px-12">
			            <p className="text-center text-[11px] font-mono uppercase tracking-[0.22em] text-white/42">Operational impact</p>
			            <div className="mt-12 grid gap-px overflow-hidden rounded-[26px] border border-white/8 bg-white/8 sm:grid-cols-2 xl:grid-cols-4">
			              {stats.map((item) => (
			                <div key={item.label} className="flex min-h-[180px] flex-col items-center justify-center bg-[#06080b] px-6 py-8 text-center">
			                  <p className="text-[clamp(2.4rem,3.2vw,3.6rem)] font-semibold leading-none tracking-[-0.05em]">{item.value}</p>
			                  <p className="mt-4 max-w-[15ch] text-[10px] uppercase leading-6 tracking-[0.18em] text-white/50">{item.label}</p>
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
        viewport={{ once: true, amount: 0.22 }}
        className={`py-24 ${isDark ? 'bg-[#090d12]' : 'bg-[#f7f2e8]'}`}
      >
        <div className="mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[0.84fr_1.16fr] lg:items-center lg:px-8">
          <div>
            <p className={`text-[11px] font-mono uppercase tracking-[0.22em] ${themeClasses.subtle}`}>CLI Surface</p>
            <h2 className="mt-4 text-[clamp(2.8rem,5vw,4.8rem)] font-semibold leading-[0.98] tracking-[-0.05em]">
              Use Nova from the CLI without losing control, evidence, or visibility.
            </h2>
            <p className={`mt-5 max-w-xl text-base leading-8 ${themeClasses.subtleStrong}`}>
              Teams can connect services, protect upstream actions, inspect alerts, and stream runtime events from the same operational model used in the dashboard.
            </p>
          </div>

          <div className="overflow-hidden rounded-[32px] border border-white/10 bg-[#0e1319] text-white shadow-[0_35px_90px_-55px_rgba(0,0,0,0.75)]">
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
                  <span className="text-white">{row}</span>
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
          <h2 className="mt-6 text-4xl font-semibold tracking-[-0.04em]">Start governing agent behavior before it reaches production.</h2>
          <p className="mt-4 text-base leading-7 text-white/68">
            Request access for your workspace and start reviewing live actions, policy decisions, and runtime evidence in one place.
          </p>

          <form onSubmit={handleSubmit} className="mx-auto mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row">
            <input
              type="email"
              placeholder="operator@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={`min-w-0 flex-1 rounded-full px-5 py-4 outline-none transition ${themeClasses.input}`}
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

function DesktopMock() {
  return (
    <div className="relative h-full w-full overflow-visible">
	      <motion.div
	        initial={{
	          opacity: 0,
	          x: 280,
	          scale: 0.92,
	          rotate: -0.6,
	          rotateY: -18,
	          filter: 'blur(24px)',
	        }}
	        animate={{
	          opacity: 1,
	          x: 0,
	          scale: 1,
	          rotate: -2.5,
	          rotateY: 0,
	          filter: 'blur(0px)',
	        }}
	        transition={{
	          duration: 2.2,
	          delay: 0.28,
	          ease: [0.16, 1, 0.3, 1],
	        }}
	        className="absolute left-[6%] top-10 w-[150%] [transform-style:preserve-3d] lg:left-[16%] lg:top-2 lg:w-[168%]"
	      >
	        <div className="absolute inset-x-[8%] bottom-[-62px] h-36 rounded-full bg-black/55 blur-3xl" />
	        <div className="relative overflow-hidden rounded-[32px] border border-white/[0.07] bg-[#12171c] p-3 shadow-[0_95px_220px_-80px_rgba(0,0,0,0.95)]">
	          <img
	            src={dashboardPreview}
	            alt="Nova dashboard screenshot"
	            className="block h-auto w-full rounded-[24px] object-cover"
	          />
	        </div>
	      </motion.div>
    </div>
  )
}

function DataCard({ title, value, copy, isDark }) {
  return (
    <div className={`rounded-[24px] border p-5 ${isDark ? 'border-white/10 bg-white/[0.04]' : 'border-black/8 bg-[#fdfaf4]'}`}>
      <p className={`text-[10px] font-semibold uppercase tracking-[0.2em] ${isDark ? 'text-white/42' : 'text-black/42'}`}>{title}</p>
      <p className={`mt-3 text-xl font-semibold tracking-[-0.03em] ${isDark ? 'text-white' : 'text-[#111111]'}`}>{value}</p>
      <p className={`mt-3 text-sm leading-7 ${isDark ? 'text-white/64' : 'text-black/62'}`}>{copy}</p>
    </div>
  )
}

export default Landing

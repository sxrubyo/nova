import React, { useContext, useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Bot, CalendarDays, ShieldCheck, Sparkles, UserRound } from 'lucide-react'
import { AuthContext } from '../pages/AuthContext'
import { novaBrandAssets } from '@/lib/nova-brand-assets'
const GENERIC_NAMES = new Set(['Admin User', 'User', 'Operator'])

const laneOptions = [
  { value: 'nova', label: 'Nova first', detail: 'Governance, controls, audit, and policy decisions.' },
  { value: 'melissa', label: 'Melissa first', detail: 'Build, iterate, and help execute operator workflows.' },
  { value: 'both', label: 'Both lanes', detail: 'Use Nova for control and Melissa for execution support.' },
]

function initialPreferredName(user) {
  if (user?.preferredName) return user.preferredName
  if (user?.name && !GENERIC_NAMES.has(user.name)) return user.name
  return ''
}

function PostLoginOnboarding() {
  const { isAuthenticated, user, completeOnboarding } = useContext(AuthContext)
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(() => ({
    preferredName: initialPreferredName(user),
    roleTitle: user?.roleTitle || '',
    birthDate: user?.birthDate || '',
    defaultAssistant: user?.defaultAssistant || 'both',
  }))

  const isOpen = Boolean(isAuthenticated && !user?.onboardingCompletedAt)
  const totalSteps = 3
  const progress = useMemo(() => ((step + 1) / totalSteps) * 100, [step])

  useEffect(() => {
    if (!isOpen) return
    setStep(0)
    setError('')
    setForm({
      preferredName: initialPreferredName(user),
      roleTitle: user?.roleTitle || '',
      birthDate: user?.birthDate || '',
      defaultAssistant: user?.defaultAssistant || 'both',
    })
  }, [isOpen, user?.preferredName, user?.name, user?.roleTitle, user?.birthDate, user?.defaultAssistant])

  if (!isOpen) return null

  const handleNext = () => {
    if (step === 1 && (!form.preferredName.trim() || !form.roleTitle.trim())) {
      setError('Add how Nova should call you and your role before continuing.')
      return
    }
    setError('')
    setStep((current) => Math.min(totalSteps - 1, current + 1))
  }

  const handleFinish = async () => {
    if (!form.preferredName.trim() || !form.roleTitle.trim()) {
      setError('Preferred name and role are required to finish setup.')
      return
    }
    setSaving(true)
    setError('')
    try {
      await completeOnboarding({
        ownerName: user?.ownerName || user?.name || form.preferredName.trim(),
        preferredName: form.preferredName.trim(),
        name: form.preferredName.trim(),
        roleTitle: form.roleTitle.trim(),
        birthDate: form.birthDate || '',
        defaultAssistant: form.defaultAssistant,
      })
    } catch (err) {
      setError(err.message || 'Nova could not save your setup just now.')
    } finally {
      setSaving(false)
    }
  }

  const handleSkip = async () => {
    setSaving(true)
    setError('')
    try {
      await completeOnboarding({
        ownerName: user?.ownerName || user?.name || form.preferredName?.trim() || '',
        preferredName: form.preferredName?.trim() || user?.preferredName || '',
        roleTitle: form.roleTitle?.trim() || user?.roleTitle || '',
        birthDate: form.birthDate || user?.birthDate || '',
        defaultAssistant: form.defaultAssistant || user?.defaultAssistant || 'both',
      })
    } catch (err) {
      setError(err.message || 'Nova could not dismiss onboarding right now.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[90] flex items-center justify-center bg-[#0b1016]/64 px-4 py-6 backdrop-blur-xl"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 18, scale: 0.98 }}
          transition={{ duration: 0.2 }}
          className="grid w-full max-w-[1080px] overflow-hidden rounded-[34px] border border-black/8 bg-[#fcfaf6] shadow-[0_45px_120px_-42px_rgba(0,0,0,0.34)] dark:border-white/[0.08] dark:bg-[#10161d] md:grid-cols-[0.92fr_1.08fr]"
        >
          <aside className="relative hidden overflow-hidden border-r border-black/6 bg-[#11151b] text-white dark:border-white/[0.06] md:flex md:flex-col md:justify-between md:p-10">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(121,217,171,0.16),transparent_30%),radial-gradient(circle_at_85%_12%,rgba(155,194,255,0.14),transparent_28%),linear-gradient(180deg,#11151b_0%,#0c1015_72%)]" />
            <div className="relative z-10">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-[22px] border border-white/10 bg-white/[0.08] p-3">
                  <img src={novaBrandAssets.isotipoSvg} alt="Nova isotipo" className="h-full w-full object-contain brightness-0 invert" />
                </div>
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-white/44">Nova onboarding</p>
                  <p className="mt-1 text-3xl font-semibold tracking-tight">Set your operator lane</p>
                </div>
              </div>

              <div className="mt-14 space-y-8">
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-white/40">What changes here</p>
                  <h1 className="mt-4 text-5xl font-semibold leading-[0.96] tracking-[-0.05em]">
                    Nova governs. Melissa helps you move faster.
                  </h1>
                  <p className="mt-5 max-w-[30rem] text-sm leading-7 text-white/66">
                    This setup is intentionally short. Define how the platform should address you, what role you operate in, and which lane should lead first.
                  </p>
                </div>

                <div className="space-y-3">
                  {[
                    { icon: ShieldCheck, title: 'Nova', body: 'Approves, blocks, records, and explains actions before they land.' },
                    { icon: Sparkles, title: 'Melissa', body: 'Helps build flows, interpret natural language, and accelerate execution.' },
                    { icon: UserRound, title: 'Personalization', body: 'Everything here can be edited later from Settings.' },
                  ].map((item) => (
                    <div key={item.title} className="rounded-[24px] border border-white/10 bg-white/[0.05] p-4">
                      <div className="flex items-start gap-3">
                        <item.icon className="mt-0.5 h-5 w-5 text-[#79d9ab]" />
                        <div>
                          <p className="text-sm font-semibold text-white">{item.title}</p>
                          <p className="mt-1 text-sm leading-6 text-white/58">{item.body}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="relative z-10">
              <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.08]">
                <div className="h-full rounded-full bg-[#79d9ab] transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.2em] text-white/38">Step {step + 1} of {totalSteps}</p>
            </div>
          </aside>

          <section className="flex min-h-[640px] flex-col justify-between bg-[#f6efe3] px-6 py-7 text-[#111111] dark:bg-[#121922] dark:text-white md:px-10 md:py-10">
            <div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-black/40 dark:text-white/42">Operator setup</p>
                  <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[#111111] dark:text-white">
                    {step === 0 && 'How Nova and Melissa work'}
                    {step === 1 && 'Tell Nova how to address you'}
                    {step === 2 && 'Set your role and default lane'}
                  </h2>
                  <p className="mt-3 max-w-[42ch] text-sm leading-6 text-black/62 dark:text-white/62">
                    {step === 0 && 'One control layer, two distinct jobs. Nova governs the action surface. Melissa helps you build and operate faster.'}
                    {step === 1 && 'Use the name you want across the shell, assistant surfaces, and guided flows.'}
                    {step === 2 && 'Role improves defaults, and the lane choice helps the product know whether to lead with control or execution support.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleSkip}
                  disabled={saving}
                  className="rounded-full border border-black/10 bg-white/70 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-black/54 transition hover:border-black/16 hover:text-black dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-white/62 dark:hover:text-white"
                >
                  Do later
                </button>
              </div>

              {step === 0 && (
                <div className="mt-10 grid gap-4 md:grid-cols-3">
                  {[
                    {
                      icon: ShieldCheck,
                      title: 'Govern before execution',
                      copy: 'Nova scores risk, checks rules, and records every allowed or blocked decision in the ledger.',
                    },
                    {
                      icon: Bot,
                      title: 'Melissa as the builder lane',
                      copy: 'Melissa is the assistant layer for prompts, flow shaping, and practical execution help.',
                    },
                    {
                      icon: Sparkles,
                      title: 'Natural language stays valid',
                      copy: 'You can still work in large natural-language prompts. Nova keeps control over the governed action path.',
                    },
                  ].map((card) => (
                    <div key={card.title} className="rounded-[26px] border border-black/8 bg-[#fffdfa] p-5 shadow-[0_24px_55px_-45px_rgba(0,0,0,0.24)] dark:border-white/[0.08] dark:bg-white/[0.03] dark:shadow-[0_28px_70px_-48px_rgba(0,0,0,0.82)]">
                      <div className="flex h-11 w-11 items-center justify-center rounded-[16px] bg-black/[0.04] dark:bg-white/[0.05]">
                        <card.icon className="h-5 w-5 text-[#111111] dark:text-white" />
                      </div>
                      <p className="mt-5 text-lg font-semibold tracking-[-0.03em] text-[#111111] dark:text-white">{card.title}</p>
                      <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">{card.copy}</p>
                    </div>
                  ))}
                </div>
              )}

              {step === 1 && (
                <div className="mt-10 grid gap-5">
                  <Field
                    label="What should Nova call you?"
                    value={form.preferredName}
                    onChange={(value) => setForm((current) => ({ ...current, preferredName: value }))}
                    placeholder="Santiago"
                  />
                  <Field
                    label="Role"
                    value={form.roleTitle}
                    onChange={(value) => setForm((current) => ({ ...current, roleTitle: value }))}
                    placeholder="AI System Architect"
                  />
                </div>
              )}

              {step === 2 && (
                <div className="mt-10 space-y-6">
                  <Field
                    label="Birth date"
                    type="date"
                    value={form.birthDate}
                    onChange={(value) => setForm((current) => ({ ...current, birthDate: value }))}
                    helper="Optional, but useful if you want a more personal operator profile."
                  />

                  <div>
                    <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-black/42 dark:text-white/42">Default lead lane</p>
                    <div className="mt-4 grid gap-3">
                      {laneOptions.map((option) => {
                        const active = form.defaultAssistant === option.value
                        return (
                          <button
                            key={option.value}
                            type="button"
                            onClick={() => setForm((current) => ({ ...current, defaultAssistant: option.value }))}
                            className={`rounded-[22px] border px-4 py-4 text-left transition ${
                              active
                                ? 'border-[#111111]/12 bg-[#111111] text-white dark:border-[#79d9ab]/30 dark:bg-[#79d9ab]/12'
                                : 'border-black/8 bg-[#fffdfa] text-[#111111] hover:border-black/14 hover:bg-white dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-white dark:hover:bg-white/[0.05]'
                            }`}
                          >
                            <p className="text-sm font-semibold">{option.label}</p>
                            <p className={`mt-1 text-sm leading-6 ${active ? 'text-white/68 dark:text-white/74' : 'text-black/60 dark:text-white/60'}`}>{option.detail}</p>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-6 rounded-[18px] border border-red-500/15 bg-red-500/8 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                  {error}
                </div>
              )}
            </div>

            <div className="mt-8 flex items-center justify-between gap-3 border-t border-black/8 pt-6 dark:border-white/[0.08]">
              <button
                  type="button"
                  onClick={() => setStep((current) => Math.max(0, current - 1))}
                  disabled={step === 0 || saving}
                  className="rounded-full border border-black/10 bg-white/80 px-5 py-3 text-sm font-semibold text-[#111111] transition hover:border-black/16 disabled:cursor-not-allowed disabled:opacity-45 dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-white"
                >
                  Back
              </button>

              {step < totalSteps - 1 ? (
                <button
                  type="button"
                  onClick={handleNext}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-full bg-[#111111] px-6 py-3 text-sm font-semibold text-white transition hover:bg-black dark:bg-white dark:text-[#111111]"
                >
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleFinish}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-full bg-[#111111] px-6 py-3 text-sm font-semibold text-white transition hover:bg-black dark:bg-white dark:text-[#111111]"
                >
                  {saving ? 'Saving…' : 'Finish setup'}
                  <ArrowRight className="h-4 w-4" />
                </button>
              )}
            </div>
          </section>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function Field({ label, helper, value, onChange, type = 'text', placeholder = '' }) {
  return (
    <label className="block">
      <div className="mb-2 text-[11px] font-mono uppercase tracking-[0.2em] text-black/42 dark:text-white/42">{label}</div>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-[20px] border border-black/8 bg-[#fffdfa] px-4 py-3.5 text-sm text-[#111111] outline-none transition focus:border-black/16 focus:bg-white dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-white dark:focus:border-white/[0.16]"
      />
      {helper && <div className="mt-2 text-sm leading-6 text-black/54 dark:text-white/54">{helper}</div>}
    </label>
  )
}

export default PostLoginOnboarding

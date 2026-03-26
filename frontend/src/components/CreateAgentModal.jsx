import React, { useContext, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Sparkles, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { api } from '../utils/api'
import { AuthContext } from '../pages/AuthContext'

const templates = [
  {
    label: 'Support',
    purpose: 'Handles inbound support conversations, summarizes context, and drafts safe customer replies.',
    allowed: 'Answer FAQs, summarize tickets, check order status, escalate billing disputes.',
    restricted: 'Do not issue refunds over 200 USD, promise delivery dates without verification, or expose customer data.',
  },
  {
    label: 'Sales',
    purpose: 'Qualifies leads, drafts outreach, and schedules meetings for account executives.',
    allowed: 'Draft outreach, update CRM notes, score lead quality, propose meeting slots.',
    restricted: 'Do not send bulk outbound campaigns without approval, claim unsupported features, or negotiate discounts over 10%.',
  },
  {
    label: 'Ops',
    purpose: 'Monitors infrastructure events, summarizes incidents, and creates internal escalation notes.',
    allowed: 'Read monitoring signals, draft incident notes, open internal tickets, notify on-call staff.',
    restricted: 'Do not rotate production credentials, delete resources, or change firewall rules automatically.',
  },
]

function CreateAgentModal({ isOpen, onClose, onCreated }) {
  const { user } = useContext(AuthContext)
  const [step, setStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    purpose: '',
    allowed: '',
    restricted: '',
    owner: user?.email || 'security@nova-os.com',
  })

  const composedDescription = useMemo(() => {
    return [
      `Agent name: ${formData.name || 'Unnamed agent'}.`,
      `Primary mission: ${formData.purpose || 'Not defined yet.'}`,
      formData.allowed ? `Allowed actions: ${formData.allowed}` : null,
      formData.restricted ? `Restricted actions: ${formData.restricted}` : null,
      `Authorized by: ${formData.owner || 'security@nova-os.com'}.`,
    ].filter(Boolean).join(' ')
  }, [formData])

  const reset = () => {
    setStep(1)
    setIsSubmitting(false)
    setError('')
    setResult(null)
    setFormData({
      name: '',
      purpose: '',
      allowed: '',
      restricted: '',
      owner: user?.email || 'security@nova-os.com',
    })
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const applyTemplate = (template) => {
    setFormData((current) => ({
      ...current,
      purpose: template.purpose,
      allowed: template.allowed,
      restricted: template.restricted,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (step === 1) {
      setStep(2)
      return
    }

    setIsSubmitting(true)
    try {
      const response = await api.post('/tokens/from-description', {
        description: composedDescription,
        authorized_by: formData.owner || user?.email || 'security@nova-os.com',
      })

      setResult(response)
      await onCreated?.(response)
      setTimeout(() => {
        handleClose()
      }, 1400)
    } catch (err) {
      setError(err.message || 'Failed to create agent')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="absolute inset-0 bg-[#05070a]/72 backdrop-blur-sm"
          />

          <motion.div
            initial={{ y: 18, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 18, opacity: 0, scale: 0.98 }}
            transition={{ type: 'spring', damping: 24, stiffness: 230 }}
            className="relative w-full max-w-3xl overflow-hidden rounded-[32px] border border-black/10 bg-[#fcfaf6] shadow-[0_50px_140px_-40px_rgba(0,0,0,0.45)]"
          >
            <div className="grid gap-0 md:grid-cols-[0.88fr_1.12fr]">
              <aside className="border-b border-black/8 bg-[#11151b] p-8 text-white md:border-b-0 md:border-r md:border-r-white/8">
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-white/70">
                  <Sparkles className="h-3.5 w-3.5" />
                  Guided Creation
                </div>
                <h3 className="mt-6 text-3xl font-semibold tracking-[-0.04em]">
                  Create an agent with governance rules, not just a name.
                </h3>
                <p className="mt-4 text-sm leading-7 text-white/68">
                  Nova turns an operational brief into an intent token with explicit permissions and restrictions.
                </p>

                <div className="mt-8 space-y-3">
                  {templates.map((template) => (
                    <button
                      key={template.label}
                      type="button"
                      onClick={() => applyTemplate(template)}
                      className="w-full rounded-2xl border border-white/10 bg-white/6 px-4 py-4 text-left transition hover:border-white/18 hover:bg-white/9"
                    >
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/50">{template.label}</p>
                      <p className="mt-2 text-sm text-white/88">{template.purpose}</p>
                    </button>
                  ))}
                </div>
              </aside>

              <section className="p-8 md:p-9">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-black/42">Agent setup</p>
                    <h4 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#111111]">
                      {step === 1 ? 'Define the operator brief' : 'Review and mint governance token'}
                    </h4>
                  </div>
                  <button onClick={handleClose} className="rounded-full p-2 text-black/42 transition hover:bg-black/5 hover:text-black">
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                  {error && (
                    <div className="rounded-2xl border border-red-500/18 bg-red-500/8 px-4 py-3 text-sm text-red-700">
                      {error}
                    </div>
                  )}

                  {result && (
                    <div className="rounded-[24px] border border-[#3ecf8e]/20 bg-[#3ecf8e]/10 p-4 text-[#104b34]">
                      <div className="flex items-center gap-2 text-sm font-semibold">
                        <CheckCircle2 className="h-4 w-4" />
                        Agent created
                      </div>
                      <p className="mt-2 text-sm">
                        `{result.agent_name}` was created with {result.can_do?.length || 0} allowed actions and {result.cannot_do?.length || 0} restricted actions.
                      </p>
                    </div>
                  )}

                  {step === 1 ? (
                    <>
                      <Field
                        label="Agent name"
                        value={formData.name}
                        onChange={(value) => setFormData((current) => ({ ...current, name: value }))}
                        placeholder="Nova Support Guard"
                        required
                      />
                      <Field
                        label="Primary mission"
                        value={formData.purpose}
                        onChange={(value) => setFormData((current) => ({ ...current, purpose: value }))}
                        placeholder="Describe what this agent should do in production."
                        required
                        multiline
                      />
                      <Field
                        label="Allowed scope"
                        value={formData.allowed}
                        onChange={(value) => setFormData((current) => ({ ...current, allowed: value }))}
                        placeholder="Examples: answer FAQs, check order status, create tickets."
                        multiline
                      />
                      <Field
                        label="Restrictions"
                        value={formData.restricted}
                        onChange={(value) => setFormData((current) => ({ ...current, restricted: value }))}
                        placeholder="Examples: never issue refunds over 200 USD or expose personal data."
                        multiline
                      />
                    </>
                  ) : (
                    <>
                      <Field
                        label="Authorized by"
                        value={formData.owner}
                        onChange={(value) => setFormData((current) => ({ ...current, owner: value }))}
                        placeholder="security@nova-os.com"
                        required
                      />

                      <div className="rounded-[26px] border border-black/8 bg-[#f6f1e6] p-5">
                        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-black/45">
                          <ShieldCheck className="h-4 w-4" />
                          Governance prompt preview
                        </div>
                        <p className="mt-4 text-sm leading-7 text-black/72">{composedDescription}</p>
                      </div>
                    </>
                  )}

                  <div className="flex gap-3 pt-2">
                    {step === 2 && (
                      <button
                        type="button"
                        onClick={() => setStep(1)}
                        className="flex-1 rounded-2xl border border-black/8 bg-white px-5 py-4 text-sm font-semibold text-black/72 transition hover:bg-[#fbf8f1]"
                      >
                        Back
                      </button>
                    )}
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="flex-[1.4] rounded-2xl bg-[#111111] px-5 py-4 text-sm font-semibold text-white shadow-[0_24px_60px_-32px_rgba(0,0,0,0.55)] transition hover:-translate-y-0.5 hover:bg-black disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isSubmitting ? 'Creating agent...' : step === 1 ? 'Continue' : 'Create agent'}
                    </button>
                  </div>
                </form>
              </section>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

function Field({ label, value, onChange, placeholder, required = false, multiline = false }) {
  const sharedClassName = 'w-full rounded-2xl border border-black/8 bg-[#f6f1e6] px-4 py-3.5 text-sm text-[#111111] placeholder:text-black/36 outline-none transition focus:border-black/15 focus:bg-white focus:ring-4 focus:ring-black/[0.03]'

  return (
    <label className="block">
      <span className="mb-2 block text-[10px] font-mono uppercase tracking-[0.18em] text-black/45">{label}</span>
      {multiline ? (
        <textarea
          rows={4}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          required={required}
          className={`${sharedClassName} resize-none`}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          required={required}
          className={sharedClassName}
        />
      )}
    </label>
  )
}

export default CreateAgentModal

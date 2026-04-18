import React, { useContext, useEffect, useState } from 'react'
import { API_BASE_PATH, SERVER_ORIGIN } from '../config/appConfig'
import { AuthContext } from './AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { motion } from 'framer-motion'
import {
  Globe,
  Shield,
  Key,
  Server,
  Database,
  RefreshCcw,
  Check,
  ChevronDown,
  UserRound,
  BriefcaseBusiness,
  CalendarDays,
  Sparkles,
} from 'lucide-react'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }
}

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 }
}

const laneOptions = [
  {
    value: 'nova',
    label: 'Nova first',
    description: 'Lead with governance, approvals, traceability, and policy.'
  },
  {
    value: 'melissa',
    label: 'Melissa first',
    description: 'Lead with build support, guided execution, and operator assistance.'
  },
  {
    value: 'both',
    label: 'Both lanes',
    description: 'Keep Nova on control and Melissa on execution support.'
  },
]

function Settings() {
  const { apiKey, setApiKey, user, updateProfile, resetOnboarding } = useContext(AuthContext)
  const { lang, setLang, t } = useLanguage()
  const [isSaved, setIsSaved] = useState(false)
  const [isSavingProfile, setIsSavingProfile] = useState(false)
  const [isReopening, setIsReopening] = useState(false)
  const [error, setError] = useState('')
  const [profileForm, setProfileForm] = useState({
    ownerName: user?.ownerName || user?.name || '',
    preferredName: user?.preferredName || '',
    roleTitle: user?.roleTitle || '',
    birthDate: user?.birthDate || '',
    defaultAssistant: user?.defaultAssistant || 'both',
  })

  const [localSettings, setLocalSettings] = useState({
    serverUrl: `${SERVER_ORIGIN}${API_BASE_PATH}`,
    debugMode: localStorage.getItem('nova_debug') === 'true',
  })

  useEffect(() => {
    setProfileForm({
      ownerName: user?.ownerName || user?.name || '',
      preferredName: user?.preferredName || '',
      roleTitle: user?.roleTitle || '',
      birthDate: user?.birthDate || '',
      defaultAssistant: user?.defaultAssistant || 'both',
    })
  }, [user?.ownerName, user?.name, user?.preferredName, user?.roleTitle, user?.birthDate, user?.defaultAssistant])

  const languages = [
    { name: 'English', code: 'en' },
    { name: 'Español', code: 'es' },
  ]

  const handleSave = async () => {
    setIsSavingProfile(true)
    setError('')
    try {
      localStorage.setItem('nova_debug', String(localSettings.debugMode))
      await updateProfile({
        ownerName: profileForm.ownerName.trim() || user?.ownerName || user?.name || '',
        preferredName: profileForm.preferredName.trim(),
        roleTitle: profileForm.roleTitle.trim(),
        birthDate: profileForm.birthDate || '',
        defaultAssistant: profileForm.defaultAssistant,
      })
      setIsSaved(true)
      setTimeout(() => setIsSaved(false), 2000)
    } catch (err) {
      setError(err.message || 'Nova could not save your settings just now.')
    } finally {
      setIsSavingProfile(false)
    }
  }

  const handleReopenOnboarding = async () => {
    setIsReopening(true)
    setError('')
    try {
      await resetOnboarding()
      setIsSaved(false)
    } catch (err) {
      setError(err.message || 'Nova could not reopen onboarding.')
    } finally {
      setIsReopening(false)
    }
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="mx-auto max-w-5xl space-y-10 pb-20"
    >
      <div className="flex flex-col justify-between gap-4 border-b border-black/5 pb-8 dark:border-white/5 md:flex-row md:items-end">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-primary dark:text-white">{t('settings')}</h2>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">
            Configure operator identity, Nova and Melissa defaults, security access, and local workspace behavior.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSavingProfile}
          className="btn-primary flex items-center gap-2 px-8 py-2.5 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isSaved ? <Check className="h-4 w-4" /> : <RefreshCcw className={`h-4 w-4 ${isSavingProfile ? 'animate-spin' : ''}`} />}
          {isSaved ? 'Saved' : isSavingProfile ? 'Saving…' : t('save_changes')}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-3">
        <div className="space-y-1">
          <SectionNav icon={UserRound} label="Profile & Personalization" active />
          <SectionNav icon={Globe} label="Localization" />
          <SectionNav icon={Shield} label="Security & API" />
          <SectionNav icon={Database} label="System Engine" />
        </div>

        <div className="space-y-12 lg:col-span-2">
          <motion.section variants={item} className="space-y-6">
            <h3 className="border-b border-black/5 pb-2 text-sm font-black uppercase tracking-widest text-black/40 dark:border-white/5 dark:text-white/40">
              Profile & Personalization
            </h3>

            <div className="grid gap-5 md:grid-cols-2">
              <Field
                label="Account owner"
                icon={UserRound}
                value={profileForm.ownerName}
                onChange={(value) => setProfileForm((current) => ({ ...current, ownerName: value }))}
                placeholder="Santiago"
              />
              <Field
                label="Login email"
                icon={Key}
                value={user?.email || ''}
                readOnly
                helper="This is the credential currently bound to your web session."
              />
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <Field
                label="How should Nova call you?"
                icon={Sparkles}
                value={profileForm.preferredName}
                onChange={(value) => setProfileForm((current) => ({ ...current, preferredName: value }))}
                placeholder="Santiago"
                helper="Used in the shell, assistant surfaces, and guided flows."
              />
              <Field
                label="Role"
                icon={BriefcaseBusiness}
                value={profileForm.roleTitle}
                onChange={(value) => setProfileForm((current) => ({ ...current, roleTitle: value }))}
                placeholder="AI System Architect"
                helper="Improves defaults for governance, guidance, and tone."
              />
            </div>

            <Field
              label="Birth date"
              icon={CalendarDays}
              type="date"
              value={profileForm.birthDate}
              onChange={(value) => setProfileForm((current) => ({ ...current, birthDate: value }))}
              helper="Optional, but available if you want a more personal operator profile."
            />

            <div className="space-y-3">
              <label className="text-xs font-black uppercase tracking-wider text-primary dark:text-white">Default assistant lane</label>
              <div className="grid gap-3">
                {laneOptions.map((option) => {
                  const active = profileForm.defaultAssistant === option.value
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setProfileForm((current) => ({ ...current, defaultAssistant: option.value }))}
                      className={`rounded-2xl border px-4 py-4 text-left transition-all ${
                        active
                          ? 'bg-black text-white shadow-sm dark:bg-white dark:text-black'
                          : 'border-black/8 bg-white text-[#111111] hover:border-black/14 dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-white dark:hover:bg-white/[0.05]'
                      }`}
                    >
                      <p className="text-sm font-bold">{option.label}</p>
                      <p className={`mt-1 text-sm leading-6 ${active ? 'text-white/70 dark:text-black/70' : 'text-black/55 dark:text-white/55'}`}>
                        {option.description}
                      </p>
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="rounded-2xl border border-black/6 bg-[#fbf8f1] p-5 dark:border-white/[0.08] dark:bg-white/[0.03]">
              <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <div>
                  <p className="text-xs font-black uppercase tracking-widest text-black/42 dark:text-white/42">Guided setup</p>
                  <p className="mt-2 text-sm leading-6 text-black/62 dark:text-white/62">
                    If you want to revisit the short post-login setup, Nova can reopen it on your next dashboard load.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleReopenOnboarding}
                  disabled={isReopening}
                  className="rounded-xl border border-black/10 bg-white px-4 py-3 text-xs font-black uppercase tracking-widest text-[#111111] transition hover:border-black/16 dark:border-white/[0.08] dark:bg-white/[0.04] dark:text-white"
                >
                  {isReopening ? 'Preparing…' : 'Run setup again'}
                </button>
              </div>
            </div>
          </motion.section>

          <motion.section variants={item} className="space-y-6">
            <h3 className="border-b border-black/5 pb-2 text-sm font-black uppercase tracking-widest text-black/40 dark:border-white/5 dark:text-white/40">
              Localization
            </h3>

            <div className="space-y-2">
              <label className="text-xs font-black uppercase tracking-wider text-primary dark:text-white">{t('language')}</label>
              <div className="group relative">
                <select
                  value={lang}
                  onChange={(event) => setLang(event.target.value)}
                  className="w-full cursor-pointer appearance-none rounded-xl border border-black/10 bg-white px-4 py-3 text-sm font-bold transition-all focus:outline-none focus:ring-2 focus:ring-accent/50 dark:border-white/10 dark:bg-[#000000]"
                >
                  {languages.map((language) => (
                    <option key={language.code} value={language.code}>{language.name}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/40 transition-colors group-hover:text-primary" />
              </div>
            </div>
          </motion.section>

          <motion.section variants={item} className="space-y-6">
            <h3 className="border-b border-black/5 pb-2 text-sm font-black uppercase tracking-widest text-black/40 dark:border-white/5 dark:text-white/40">
              Security & API
            </h3>

            <div className="space-y-4">
              <Field
                label="Workspace API Key"
                icon={Key}
                type="password"
                value={apiKey}
                onChange={setApiKey}
                helper="Used for direct workspace access when you want to bypass the web session."
              />

              <Field
                label="API Endpoint URL"
                icon={Server}
                value={localSettings.serverUrl}
                readOnly
              />
            </div>
          </motion.section>

          <motion.section variants={item} className="space-y-6">
            <h3 className="border-b border-black/5 pb-2 text-sm font-black uppercase tracking-widest text-black/40 dark:border-white/5 dark:text-white/40">
              System Engine
            </h3>

            <label className="flex items-center justify-between rounded-2xl border border-black/6 bg-[#fbf8f1] px-5 py-4 dark:border-white/[0.08] dark:bg-white/[0.03]">
              <div>
                <p className="text-sm font-bold text-[#111111] dark:text-white">Verbose local debug mode</p>
                <p className="mt-1 text-sm text-black/55 dark:text-white/55">
                  Keeps richer local diagnostics for development and operator troubleshooting.
                </p>
              </div>
              <input
                type="checkbox"
                checked={localSettings.debugMode}
                onChange={(event) => setLocalSettings((current) => ({ ...current, debugMode: event.target.checked }))}
                className="h-5 w-5 rounded border-black/20 accent-black"
              />
            </label>
          </motion.section>

          {error && (
            <motion.div variants={item} className="rounded-2xl border border-red-500/10 bg-red-500/5 px-5 py-4 text-sm text-red-600 dark:text-red-300">
              {error}
            </motion.div>
          )}

          <motion.section variants={item} className="border-t border-red-500/10 pt-8">
            <div className="flex flex-col justify-between gap-6 rounded-2xl border border-red-500/10 bg-red-500/5 p-6 md:flex-row md:items-center">
              <div>
                <h4 className="text-sm font-black uppercase tracking-widest text-red-500">Danger Zone</h4>
                <p className="mt-1 text-xs font-bold text-red-500/60">Permanently delete all local session data.</p>
              </div>
              <button
                onClick={() => {
                  if (confirm('Purge all data?')) {
                    localStorage.clear()
                    window.location.reload()
                  }
                }}
                className="rounded-xl bg-red-500 px-6 py-2 text-xs font-black uppercase tracking-widest text-white transition-colors hover:bg-red-600"
              >
                Factory Reset
              </button>
            </div>
          </motion.section>
        </div>
      </div>
    </motion.div>
  )
}

function SectionNav({ icon: Icon, label, active = false }) {
  return (
    <button className={`w-full rounded-xl px-4 py-3 text-sm font-bold transition-all ${active ? 'bg-black text-white shadow-sm dark:bg-white dark:text-black' : 'text-black/40 hover:bg-black/5 dark:text-white/40 dark:hover:bg-white/5'}`}>
      <span className="flex items-center gap-3">
        <Icon className="h-4 w-4" />
        {label}
      </span>
    </button>
  )
}

function Field({ label, icon: Icon, helper, value, onChange, type = 'text', placeholder = '', readOnly = false }) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-black uppercase tracking-wider text-primary dark:text-white">{label}</label>
      <div className="relative">
        {Icon ? <Icon className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/20" /> : null}
        <input
          type={type}
          value={value}
          onChange={(event) => onChange?.(event.target.value)}
          placeholder={placeholder}
          readOnly={readOnly}
          className={`w-full rounded-xl border border-black/5 bg-[#fbf8f1] py-3 text-sm text-[#111111] shadow-inner transition-all focus:outline-none dark:border-white/5 dark:bg-white/[0.05] dark:text-white ${
            Icon ? 'pl-12 pr-4' : 'px-4'
          } ${readOnly ? 'cursor-not-allowed text-black/45 dark:text-white/45' : ''}`}
        />
      </div>
      {helper ? <p className="text-sm text-black/55 dark:text-white/55">{helper}</p> : null}
    </div>
  )
}

export default Settings

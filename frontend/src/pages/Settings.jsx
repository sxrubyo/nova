import React, { useState, useContext } from 'react'
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
  Bell,
  Check,
  ChevronDown
} from 'lucide-react'

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } }
}

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 }
}

function Settings() {
  const { apiKey, setApiKey } = useContext(AuthContext)
  const { lang, setLang, t } = useLanguage()
  const [isSaved, setIsSaved] = useState(false)
  
  const [localSettings, setLocalSettings] = useState({
    serverUrl: `${SERVER_ORIGIN}${API_BASE_PATH}`,
    debugMode: localStorage.getItem('nova_debug') === 'true',
  })

  const languages = [
    { name: 'English', code: 'en' },
    { name: 'Español', code: 'es' },
  ]

  const handleSave = () => {
    localStorage.setItem('nova_debug', localSettings.debugMode)
    setIsSaved(true)
    setTimeout(() => setIsSaved(false), 2000)
  }

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="max-w-5xl mx-auto space-y-10 pb-20"
    >
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-black/5 dark:border-white/5 pb-8">
        <div>
          <h2 className="text-3xl font-bold text-primary dark:text-white tracking-tight">{t('settings')}</h2>
          <p className="text-black/60 dark:text-white/60 text-sm mt-1">Configure your workspace governance parameters and interface.</p>
        </div>
        <button 
          onClick={handleSave}
          className="btn-primary px-8 py-2.5 flex items-center gap-2"
        >
          {isSaved ? <Check className="w-4 h-4" /> : <RefreshCcw className="w-4 h-4" />}
          {isSaved ? 'OK' : t('save_changes')}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div className="space-y-1">
          <SectionNav icon={Globe} label="Localization" active />
          <SectionNav icon={Shield} label="Security & API" />
          <SectionNav icon={Database} label="System Engine" />
        </div>

        <div className="lg:col-span-2 space-y-12">
          {/* Localization Section */}
          <motion.section variants={item} className="space-y-6">
            <h3 className="text-sm font-black uppercase tracking-widest text-black/40 dark:text-white/40 border-b border-black/5 dark:border-white/5 pb-2">Localization</h3>
            
            <div className="space-y-2">
              <label className="text-xs font-black text-primary dark:text-white uppercase tracking-wider">{t('language')}</label>
              <div className="relative group">
                <select 
                  value={lang}
                  onChange={(e) => setLang(e.target.value)}
                  className="w-full bg-white dark:bg-[#000000] border border-black/10 dark:border-white/10 rounded-xl px-4 py-3 text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all cursor-pointer font-bold"
                >
                  {languages.map(l => (
                    <option key={l.code} value={l.code}>{l.name}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-black/40 pointer-events-none group-hover:text-primary transition-colors" />
              </div>
            </div>
          </motion.section>

          {/* Security Section */}
          <motion.section variants={item} className="space-y-6">
            <h3 className="text-sm font-black uppercase tracking-widest text-black/40 dark:text-white/40 border-b border-black/5 dark:border-white/5 pb-2">Security & API</h3>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-black text-primary dark:text-white uppercase tracking-wider">Workspace API Key</label>
                <div className="relative flex-1">
                  <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-black/20" />
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full bg-[#fbf8f1] dark:bg-white/5 border border-black/5 dark:border-white/5 rounded-xl pl-12 pr-4 py-3 text-[#111111] dark:text-white font-mono text-xs focus:outline-none focus:border-accent/50 transition-all shadow-inner"
                  />
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <label className="text-xs font-black text-primary dark:text-white uppercase tracking-wider">API Endpoint URL</label>
                <div className="relative">
                  <Server className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-black/20" />
                  <input
                    type="text"
                    readOnly
                    value={localSettings.serverUrl}
                    className="w-full bg-[#fbf8f1] dark:bg-white/5 border border-black/5 dark:border-white/5 rounded-xl pl-12 pr-4 py-3 text-black/40 dark:text-white/40 font-mono text-xs focus:outline-none shadow-inner cursor-not-allowed"
                  />
                </div>
              </div>
            </div>
          </motion.section>

          {/* Danger Zone */}
          <motion.section variants={item} className="pt-8 border-t border-red-500/10">
            <div className="p-6 rounded-2xl bg-red-500/5 border border-red-500/10 flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <h4 className="text-sm font-black text-red-500 uppercase tracking-widest">Danger Zone</h4>
                <p className="text-xs text-red-500/60 mt-1 font-bold">Permanently delete all local session data.</p>
              </div>
              <button 
                onClick={() => {
                  if(confirm('Purge all data?')) {
                    localStorage.clear();
                    window.location.reload();
                  }
                }}
                className="px-6 py-2 bg-red-500 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-red-600 transition-colors shadow-lg shadow-red-500/20"
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
    <button className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all ${active ? 'bg-black dark:bg-white text-white dark:text-black shadow-sm' : 'text-black/40 dark:text-white/40 hover:bg-black/5 dark:hover:bg-white/5'}`}>
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}

export default Settings

import React, { useContext, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Ledger from './pages/Ledger'
import Agents from './pages/Agents'
import Skills from './pages/Skills'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Landing from './pages/Landing'
import { AuthContext, AuthProvider } from './pages/AuthContext'
import { api } from './utils/api'

import { ThemeProvider, useTheme } from './context/ThemeContext'
import { LanguageProvider, useLanguage } from './context/LanguageContext'
import SplashScreen from './components/SplashScreen'
import {
  BadgeCheck,
  Bot,
  Camera,
  Cpu,
  FileText,
  LayoutDashboard,
  LogOut,
  Moon,
  Orbit,
  Search,
  Settings as SettingsIcon,
  ShieldCheck,
  Sun,
  User,
} from 'lucide-react'

const novaIsotipoBlack = new URL('../nova-branding/Nova I/Black Nova Isotipo.png', import.meta.url).href
const novaIsotipoWhite = new URL('../nova-branding/Nova I/White Nova Isotipo.png', import.meta.url).href

const routeMeta = {
  '/dashboard': {
    title: 'Operator Dashboard',
    subtitle: 'See what needs attention across agents, models, alerts, and runtime decisions.',
  },
  '/ledger': {
    title: 'Evidence Ledger',
    subtitle: 'Review the record of governed actions and keep the audit trail readable.',
  },
  '/agents': {
    title: 'Governed Agents',
    subtitle: 'Inspect active agents, permissions, and operational state from one surface.',
  },
  '/skills': {
    title: 'Skill Surfaces',
    subtitle: 'Manage the capabilities that agents can access under Nova governance.',
  },
  '/settings': {
    title: 'Workspace Settings',
    subtitle: 'Configure the environment, providers, and operator-level defaults.',
  },
}

function Sidebar() {
  const location = useLocation()
  const { setApiKey, setIsAuthenticated, user, setUser } = useContext(AuthContext)
  const { theme, toggleTheme } = useTheme()
  const { t } = useLanguage()
  const fileInputRef = useRef(null)

  const navItems = [
    { path: '/dashboard', label: t('dashboard'), description: 'Runtime, alerts, and operator actions', icon: LayoutDashboard },
    { path: '/ledger', label: t('ledger'), description: 'Decisions, evidence, and trace history', icon: FileText },
    { path: '/agents', label: t('agents'), description: 'Governed agents and active tokens', icon: Bot },
    { path: '/skills', label: t('skills'), description: 'Capabilities available to the workspace', icon: Cpu },
    { path: '/settings', label: t('settings'), description: 'Providers, policies, and workspace config', icon: SettingsIcon },
  ]

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setUser({ ...user, avatar: reader.result })
      }
      reader.readAsDataURL(file)
    }
  }

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout', {})
    } catch (err) {
      console.error('Logout failed:', err)
    } finally {
      setApiKey('')
      setIsAuthenticated(false)
      window.location.href = '/login'
    }
  }

  return (
    <aside className="sticky top-0 z-40 flex min-h-screen w-[290px] flex-col border-r border-black/6 bg-[#f8f3eb]/92 px-5 py-5 backdrop-blur-xl dark:border-white/[0.05] dark:bg-[#0f1419]/92">
      <div className="rounded-[28px] border border-black/8 bg-white/86 p-4 shadow-[0_18px_45px_-35px_rgba(0,0,0,0.35)] dark:border-white/[0.06] dark:bg-white/[0.03] dark:shadow-[0_26px_60px_-42px_rgba(0,0,0,0.9)]">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-black/[0.04] dark:bg-white/[0.05]">
            <img
              src={theme === 'dark' ? novaIsotipoWhite : novaIsotipoBlack}
              alt="Nova logo"
              className="h-9 w-9 object-contain"
            />
          </div>
          <div>
            <p className="text-base font-semibold tracking-[-0.03em] text-black dark:text-[#f2f4f6]">Nova OS</p>
            <p className="text-xs text-black/52 dark:text-[#8e959d]">Govern what your agents can do.</p>
          </div>
        </div>

        <div className="mt-4 rounded-[22px] border border-[#3ecf8e]/16 bg-[#3ecf8e]/10 px-4 py-3">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-4 w-4 text-[#2d9d63]" />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#2d9d63]">Workspace live</p>
              <p className="mt-1 text-sm leading-6 text-black/60 dark:text-white/62">
                Nova is framed as an operator product now: clearer context, clearer actions, clearer model control.
              </p>
            </div>
          </div>
        </div>
      </div>

      <nav className="mt-6 flex-1 space-y-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`group block rounded-[24px] border px-4 py-4 transition-all ${
                isActive
                  ? 'border-transparent bg-[#11161d] text-white shadow-[0_28px_70px_-42px_rgba(0,0,0,0.55)]'
                  : 'border-black/8 bg-white/72 text-black/70 hover:border-black/10 hover:bg-white dark:border-white/[0.05] dark:bg-white/[0.03] dark:text-[#a0a7af] dark:hover:bg-white/[0.05]'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 flex h-10 w-10 items-center justify-center rounded-2xl ${isActive ? 'bg-white/[0.08]' : 'bg-black/[0.04] dark:bg-white/[0.04]'}`}>
                  <item.icon className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className={`text-sm font-semibold tracking-[-0.02em] ${isActive ? 'text-white' : 'text-black dark:text-[#edf0f2]'}`}>{item.label}</p>
                  <p className={`mt-1 text-xs leading-5 ${isActive ? 'text-white/58' : 'text-black/48 dark:text-[#7f8790]'}`}>{item.description}</p>
                </div>
              </div>
            </Link>
          )
        })}
      </nav>

      <div className="space-y-4 border-t border-black/6 pt-5 dark:border-white/[0.05]">
        <div className="rounded-[24px] border border-black/8 bg-white/76 p-4 dark:border-white/[0.06] dark:bg-white/[0.03]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div
                className="group relative flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl bg-black/[0.05] dark:bg-white/[0.05]"
                onClick={() => fileInputRef.current?.click()}
              >
                {user?.avatar ? (
                  <img src={user.avatar} alt="User avatar" className="h-full w-full object-cover" />
                ) : (
                  <User className="h-5 w-5 opacity-40" />
                )}
                <div className="absolute inset-0 flex items-center justify-center bg-black/55 opacity-0 transition-opacity group-hover:opacity-100">
                  <Camera className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-black dark:text-[#edf0f2]">{user?.name || 'Operator'}</p>
                <p className="text-[11px] uppercase tracking-[0.18em] text-black/38 dark:text-[#7e858d]">Workspace operator</p>
              </div>
            </div>
            <BadgeCheck className="h-4 w-4 text-[#2f9d63]" />
          </div>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept="image/*"
          />

          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              onClick={toggleTheme}
              className="flex items-center justify-center gap-2 rounded-2xl bg-black/[0.05] px-3 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-black/55 transition hover:bg-black/[0.08] dark:bg-white/[0.05] dark:text-white/62 dark:hover:bg-white/[0.08]"
            >
              {theme === 'dark' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              Theme
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center justify-center gap-2 rounded-2xl bg-red-500/8 px-3 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-600 transition hover:bg-red-500/12"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>

        <div className="rounded-[24px] border border-black/8 bg-[#11161d] px-4 py-4 text-white shadow-[0_24px_60px_-42px_rgba(0,0,0,0.7)] dark:border-white/[0.05]">
          <div className="flex items-start gap-3">
            <Orbit className="mt-0.5 h-4 w-4 text-[#7fd9af]" />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/46">Operator tip</p>
              <p className="mt-2 text-sm leading-6 text-white/68">
                Use “Talk with your agent” to choose provider and model. If Nova has no server key, paste your own key by provider.
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}

function Header() {
  const location = useLocation()
  const [search, setSearch] = useState('')
  const meta = routeMeta[location.pathname] || {
    title: 'Nova',
    subtitle: 'Govern agent behavior with more clarity.',
  }

  return (
    <header className="sticky top-0 z-30 border-b border-black/6 bg-[#fbf7ef]/88 px-8 py-5 backdrop-blur-xl dark:border-white/[0.05] dark:bg-[#0c1014]/88">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-black/38 dark:text-[#808790]">Nova operator surface</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.05em] text-[#111111] dark:text-white">{meta.title}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-black/56 dark:text-[#8f97a0]">{meta.subtitle}</p>
        </div>

        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative min-w-[280px] lg:min-w-[360px]">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/24 dark:text-[#747b84]" />
            <input
              type="text"
              placeholder="Search pages, agents, alerts, or decisions"
              className="w-full rounded-2xl border border-black/8 bg-white/82 py-3 pl-11 pr-4 text-sm font-medium outline-none transition focus:border-black/14 focus:ring-2 focus:ring-black/5 dark:border-white/[0.06] dark:bg-white/[0.04] dark:text-[#d6dbe0] dark:placeholder:text-[#747b84] dark:focus:border-white/[0.12] dark:focus:ring-white/[0.04]"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill icon={BadgeCheck} label="Workspace live" tone="green" />
            <StatusPill icon={ShieldCheck} label="Policies active" tone="dark" />
          </div>
        </div>
      </div>
    </header>
  )
}

function StatusPill({ icon: Icon, label, tone }) {
  const toneClasses = tone === 'green'
    ? 'border-[#3ecf8e]/16 bg-[#3ecf8e]/10 text-[#277a4f]'
    : 'border-black/8 bg-white/82 text-black/55 dark:border-white/[0.06] dark:bg-white/[0.05] dark:text-white/64'

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${toneClasses}`}>
      <Icon className="h-3.5 w-3.5" />
      {label}
    </div>
  )
}

function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-[#f4efe5] text-black transition-colors duration-500 selection:bg-accent selection:text-black dark:bg-[#0b0f13] dark:text-[#d4d9de]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="relative flex-1 overflow-auto">
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute left-[-8%] top-0 h-[420px] w-[420px] rounded-full bg-[#3ecf8e]/10 blur-3xl" />
            <div className="absolute right-[-10%] top-10 h-[440px] w-[440px] rounded-full bg-[#5f7cff]/8 blur-3xl" />
          </div>
          <div className="relative px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, isAuthLoading } = useContext(AuthContext)
  if (isAuthLoading) return null
  return isAuthenticated ? <Layout>{children}</Layout> : <Navigate to="/login" />
}

function App() {
  const [showSplash, setShowSplash] = useState(true)

  return (
    <AuthProvider>
      <ThemeProvider>
        <LanguageProvider>
          <SplashScreen onFinish={() => setShowSplash(false)} />
          {!showSplash && (
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />
                <Route
                  path="/dashboard"
                  element={(
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  )}
                />
                <Route
                  path="/ledger"
                  element={(
                    <ProtectedRoute>
                      <Ledger />
                    </ProtectedRoute>
                  )}
                />
                <Route
                  path="/agents"
                  element={(
                    <ProtectedRoute>
                      <Agents />
                    </ProtectedRoute>
                  )}
                />
                <Route
                  path="/skills"
                  element={(
                    <ProtectedRoute>
                      <Skills />
                    </ProtectedRoute>
                  )}
                />
                <Route
                  path="/settings"
                  element={(
                    <ProtectedRoute>
                      <Settings />
                    </ProtectedRoute>
                  )}
                />
              </Routes>
            </BrowserRouter>
          )}
        </LanguageProvider>
      </ThemeProvider>
    </AuthProvider>
  )
}

export default App

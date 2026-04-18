import React, { useContext, useRef, useState } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { LayoutDashboard, FileText, Bot, Cpu, Settings as SettingsIcon, LogOut, Sun, Moon, User, Search, Camera, ScanSearch, Plus } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Ledger from './pages/Ledger'
import Agents from './pages/Agents'
import Skills from './pages/Skills'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Landing from './pages/Landing'
import DiscoveryCenter from './pages/dashboard/Discovery'
import DiscoveryHelp from './pages/dashboard/DiscoveryHelp'
import AgentWizard from './pages/dashboard/AgentWizard'
import { AuthContext, AuthProvider } from './pages/AuthContext'
import { api } from './utils/api'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { LanguageProvider, useLanguage } from './context/LanguageContext'
import SplashScreen from './components/SplashScreen'
import PostLoginOnboarding from './components/PostLoginOnboarding'
import { ToastRegion } from './components/ui'
import { novaBrandAssets } from './lib/nova-brand-assets'

function Sidebar() {
  const location = useLocation()
  const { setApiKey, setIsAuthenticated, user, setUser } = useContext(AuthContext)
  const { theme, toggleTheme } = useTheme()
  const { t } = useLanguage()
  const fileInputRef = useRef(null)

  const navItems = [
    { path: '/dashboard', label: t('dashboard'), icon: LayoutDashboard },
    { path: '/dashboard/discover', label: 'Discovery', icon: ScanSearch },
    { path: '/ledger', label: t('ledger'), icon: FileText },
    { path: '/agents', label: t('agents'), icon: Bot },
    { path: '/dashboard/agents/new', label: 'New Agent', icon: Plus },
    { path: '/skills', label: t('skills'), icon: Cpu },
    { path: '/settings', label: t('settings'), icon: SettingsIcon },
  ]

  const hasProfileLogo = Boolean(user?.avatar)

  const handleFileChange = (event) => {
    const file = event.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onloadend = () => {
      setUser({ ...user, avatar: reader.result })
    }
    reader.readAsDataURL(file)
  }

  const handleLogout = async () => {
    await api.post('/auth/logout', {}).catch(() => null)
    setApiKey('')
    setIsAuthenticated(false)
    window.location.href = '/login'
  }

  return (
    <aside className="sticky top-0 z-50 flex min-h-screen w-64 flex-col bg-[#F9F9F9] p-6 transition-colors duration-500 dark:bg-[#101316]">
      <div className="mb-12 flex items-center gap-3 bg-transparent px-1">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-black/8 bg-white/90 p-2 shadow-[0_18px_40px_-30px_rgba(0,0,0,0.22)] dark:border-white/[0.08] dark:bg-white/[0.04]">
          <img
            src={novaBrandAssets.isotipoSvg}
            alt="Nova isotipo"
            className={`h-full w-full object-contain ${theme === 'dark' ? 'brightness-0 invert' : ''}`}
          />
        </div>
        <div className="flex min-w-0 items-center gap-3">
          <span className="text-lg font-semibold tracking-tight text-black/22 dark:text-white/22">|</span>
          <p className="truncate text-lg font-bold tracking-tight text-black dark:text-[#f2f4f6]">
            {user?.name || 'Dashboard'}
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 rounded-xl px-4 py-3 text-[13px] font-bold transition-all ${
                isActive
                  ? 'bg-black text-white shadow-[0_18px_40px_-28px_rgba(0,0,0,0.75)] dark:bg-[#1b2026] dark:text-white'
                  : 'text-black/40 hover:bg-black/5 hover:text-black dark:text-[#8e959d] dark:hover:bg-white/[0.04] dark:hover:text-white'
              }`}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      <div className="space-y-6 border-t border-black/5 pt-6 dark:border-white/[0.05]">
        <div
          className="group relative flex cursor-pointer items-center gap-3 px-2"
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border border-black/8 bg-white/80 transition-all group-hover:ring-1 group-hover:ring-white/10 dark:border-white/[0.08] dark:bg-white/[0.04]">
            {user?.avatar ? (
              <img src={user.avatar} alt={user.name} className="h-full w-full object-contain p-1.5" />
            ) : (
              <User className="h-5 w-5 opacity-40" />
            )}
            <div className="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 transition-opacity group-hover:opacity-100">
              <Camera className="h-4 w-4 text-white" />
            </div>
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-bold uppercase tracking-tight text-black dark:text-[#edf0f2]">{user?.name || 'User'}</p>
            <p className="text-[9px] font-bold uppercase leading-none tracking-widest text-black/30 dark:text-[#7e858d]">
              {user?.roleTitle || 'Profile settings'}
            </p>
          </div>
          <input ref={fileInputRef} type="file" onChange={handleFileChange} className="hidden" accept="image/*" />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center rounded-xl bg-black/5 p-3 text-black/40 transition-colors hover:text-black dark:bg-white/[0.04] dark:text-[#8e959d] dark:hover:text-white"
          >
            {theme === 'dark' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center justify-center rounded-xl bg-red-500/5 p-3 text-red-500 transition-colors hover:bg-red-500/10"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}

function Header() {
  const [search, setSearch] = useState('')

  return (
    <header className="flex h-20 items-center justify-between bg-white px-10 transition-colors duration-500 dark:bg-[#0c0f12]">
      <div className="group relative w-96">
        <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-black/20 transition-colors group-focus-within:text-accent dark:text-[#747b84]" />
        <input
          type="text"
          placeholder="Search agents, nodes, skills..."
          className="w-full rounded-xl border-0 bg-black/5 py-2.5 pl-12 pr-4 text-xs font-bold outline-none transition-all placeholder:text-black/20 focus:ring-1 focus:ring-accent/30 dark:bg-white/[0.04] dark:text-[#d6dbe0] dark:placeholder:text-[#747b84]"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="h-1 w-1 rounded-full bg-accent" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-black/30 dark:text-[#7e858d]">Network Operational</span>
        </div>
        <button className="rounded-xl bg-black px-6 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-sm transition-all hover:opacity-80 dark:bg-[#edf0f2] dark:text-[#101316]">
          Sync Node
        </button>
      </div>
    </header>
  )
}

function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-white text-black transition-colors duration-500 selection:bg-accent selection:text-black dark:bg-[#0c0f12] dark:text-[#d4d9de]">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-10">{children}</main>
      </div>
      <PostLoginOnboarding />
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
          <ToastRegion />
          {!showSplash && (
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/discover"
                  element={
                    <ProtectedRoute>
                      <DiscoveryCenter />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/help/discovery"
                  element={
                    <ProtectedRoute>
                      <DiscoveryHelp />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/dashboard/agents/new"
                  element={
                    <ProtectedRoute>
                      <AgentWizard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/ledger"
                  element={
                    <ProtectedRoute>
                      <Ledger />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/agents"
                  element={
                    <ProtectedRoute>
                      <Agents />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/skills"
                  element={
                    <ProtectedRoute>
                      <Skills />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <ProtectedRoute>
                      <Settings />
                    </ProtectedRoute>
                  }
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

import React, { useState, useContext, useRef } from 'react'
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
import CreateAgentModal from './components/CreateAgentModal'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  LayoutDashboard, 
  FileText, 
  Bot, 
  Cpu, 
  Settings as SettingsIcon, 
  LogOut, 
  Sun, 
  Moon,
  User,
  Search,
  Camera
} from 'lucide-react'

const novaIsotipoBlack = new URL('../nova-branding/Nova I/Black Nova Isotipo.png', import.meta.url).href
const novaIsotipoWhite = new URL('../nova-branding/Nova I/White Nova Isotipo.png', import.meta.url).href

function Sidebar() {
  const location = useLocation()
  const { setApiKey, setIsAuthenticated, user, setUser } = useContext(AuthContext)
  const { theme, toggleTheme } = useTheme()
  const { t } = useLanguage()
  const fileInputRef = useRef(null)

  const navItems = [
    { path: '/dashboard', label: t('dashboard'), icon: LayoutDashboard },
    { path: '/ledger', label: t('ledger'), icon: FileText },
    { path: '/agents', label: t('agents'), icon: Bot },
    { path: '/skills', label: t('skills'), icon: Cpu },
    { path: '/settings', label: t('settings'), icon: SettingsIcon },
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
    <aside className="w-64 bg-[#F9F9F9] dark:bg-[#101316] min-h-screen p-6 flex flex-col z-50 sticky top-0 transition-colors duration-500">
      {/* BRANDING - Strictly Transparent PNG */}
      <div className="flex items-center gap-3 mb-12 px-2 bg-transparent">
        <img 
          src={theme === 'dark' ? novaIsotipoWhite : novaIsotipoBlack} 
          alt="Logo" 
          className="w-8 h-8 object-contain bg-transparent" 
        />
        <span className="font-bold text-lg text-black dark:text-[#f2f4f6] tracking-tighter">NOVA OS</span>
      </div>

      {/* NAVIGATION */}
      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-[13px] font-bold transition-all
                ${isActive
                  ? 'bg-black dark:bg-[#1b2026] text-white dark:text-white shadow-[0_18px_40px_-28px_rgba(0,0,0,0.75)]'
                  : 'text-black/40 dark:text-[#8e959d] hover:text-black dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/[0.04]'
                }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* USER PROFILE - Photo Selection Integrated */}
      <div className="pt-6 border-t border-black/5 dark:border-white/[0.05] space-y-6">
        <div className="group relative flex items-center gap-3 px-2 cursor-pointer" onClick={() => fileInputRef.current?.click()}>
          <div className="relative w-10 h-10 rounded-xl bg-black/5 dark:bg-white/[0.04] flex items-center justify-center overflow-hidden transition-all group-hover:ring-1 group-hover:ring-white/10">
            {user.avatar ? (
              <img src={user.avatar} className="w-full h-full object-cover" />
            ) : (
              <User className="w-5 h-5 opacity-40" />
            )}
            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
               <Camera className="w-4 h-4 text-white" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-bold truncate text-black dark:text-[#edf0f2] uppercase tracking-tight">{user.name}</p>
            <p className="text-[9px] font-bold text-black/30 dark:text-[#7e858d] uppercase tracking-widest leading-none">Settings</p>
          </div>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            className="hidden" 
            accept="image/*"
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center p-3 rounded-xl bg-black/5 dark:bg-white/[0.04] text-black/40 dark:text-[#8e959d] hover:text-black dark:hover:text-white transition-colors"
          >
            {theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center justify-center p-3 rounded-xl bg-red-500/5 text-red-500 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}

function Header() {
  const [search, setSearch] = useState('')

  return (
    <header className="h-20 flex items-center justify-between px-10 bg-white dark:bg-[#0c0f12] transition-colors duration-500">
      {/* Search Implementation */}
      <div className="relative w-96 group">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-black/20 dark:text-[#747b84] group-focus-within:text-accent transition-colors" />
        <input 
          type="text"
          placeholder="Search agents, nodes, skills..."
          className="w-full bg-black/5 dark:bg-white/[0.04] border-0 rounded-xl pl-12 pr-4 py-2.5 text-xs font-bold outline-none focus:ring-1 focus:ring-accent/30 dark:text-[#d6dbe0] placeholder:text-black/20 dark:placeholder:text-[#747b84] transition-all"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
           <span className="w-1 h-1 bg-accent rounded-full"></span>
           <span className="text-[10px] font-bold text-black/30 dark:text-[#7e858d] uppercase tracking-widest">Network Operational</span>
        </div>
        <button className="text-[10px] font-bold uppercase tracking-wider px-6 py-2.5 bg-black dark:bg-[#edf0f2] text-white dark:text-[#101316] rounded-xl hover:opacity-80 transition-all shadow-sm">
          Sync Node
        </button>
      </div>
    </header>
  )
}

function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-white dark:bg-[#0c0f12] text-black dark:text-[#d4d9de] transition-colors duration-500 selection:bg-accent selection:text-black">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-10 overflow-auto">
          {children}
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
                <Route path="/dashboard" element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                } />
                <Route path="/ledger" element={
                  <ProtectedRoute>
                    <Ledger />
                  </ProtectedRoute>
                } />
                <Route path="/agents" element={
                  <ProtectedRoute>
                    <Agents />
                  </ProtectedRoute>
                } />
                <Route path="/skills" element={
                  <ProtectedRoute>
                    <Skills />
                  </ProtectedRoute>
                } />
                <Route path="/settings" element={
                  <ProtectedRoute>
                    <Settings />
                  </ProtectedRoute>
                } />
              </Routes>
            </BrowserRouter>
          )}
        </LanguageProvider>
      </ThemeProvider>
    </AuthProvider>
  )
}

export default App

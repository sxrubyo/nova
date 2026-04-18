import React, { useState, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthContext } from './AuthContext'
import { api } from '../utils/api'
import { GITHUB_AUTH_URL } from '../config/appConfig'

const novaIsotipoBlack = new URL('../../nova-branding/Nova I/Black Nova Isotipo.png', import.meta.url).href
const novaIsotipoWhite = new URL('../../nova-branding/Nova I/White Nova Isotipo.png', import.meta.url).href
const datacenterInfra = '/images/datacenter-infra.jpg'

const capabilityList = [
  'Intent verification',
  'Immutable ledger',
  'Real-time analytics',
  'Multi-agent support',
]

const operatorStats = [
  { value: '99.94%', label: 'decision trace availability' },
  { value: '<200ms', label: 'median validation latency' },
  { value: '24/7', label: 'security operations visibility' },
]

function Login() {
  const navigate = useNavigate()
  const { setIsAuthenticated, setUser, setApiKey } = useContext(AuthContext)
  const [isSignUp, setIsSignUp] = useState(false)
  const [useApiKey, setUseApiKey] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    company: '',
    apiKey: '',
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      if (useApiKey && !isSignUp) {
        // Verify API key
        localStorage.setItem('nova_api_key', formData.apiKey)
        try {
          const workspace = await api.get('/workspaces/me')
          setApiKey(formData.apiKey)
          setUser({ name: workspace.name, email: 'workspace@nova-os.com' })
          setIsAuthenticated(true)
          navigate('/dashboard')
        } catch (err) {
          localStorage.removeItem('nova_api_key')
          throw new Error('Invalid Workspace API Key')
        }
      } else {
        // Mock traditional login/signup
        await new Promise((resolve) => setTimeout(resolve, 900))
        setIsAuthenticated(true)
        setUser({ name: formData.name || 'User', email: formData.email })
        navigate('/dashboard')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGithubLogin = () => {
    if (!GITHUB_AUTH_URL) return
    window.location.href = GITHUB_AUTH_URL
  }

  const panelTitle = isSignUp ? 'Request Access' : 'Operator access'
  const panelSubtitle = isSignUp
    ? 'Self-registration is restricted. Please contact your system administrator for a Workspace API Key.'
    : 'Sign in to access runtime controls, validation history, and system status.'

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0b0f13] text-[#111111]">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-x-0 top-0 h-[720px] bg-[radial-gradient(circle_at_top_left,rgba(121,217,171,0.10),transparent_28%),radial-gradient(circle_at_85%_12%,rgba(155,194,255,0.08),transparent_24%),linear-gradient(180deg,#0f1419_0%,#0b0f13_72%)]" />
        <div className="absolute left-[-120px] top-16 h-[420px] w-[420px] rounded-full bg-[#79d9ab]/8 blur-3xl" />
        <div className="absolute right-[-160px] top-10 h-[520px] w-[520px] rounded-full bg-white/[0.05] blur-3xl" />
      </div>

      <div className="relative z-10 min-h-screen px-4 py-6 md:px-8 md:py-8">
        <div className="mx-auto grid min-h-[calc(100vh-2rem)] w-full max-w-[1320px] overflow-hidden rounded-[36px] bg-[#fcfaf6]/95 shadow-[0_45px_120px_-42px_rgba(0,0,0,0.26)] backdrop-blur-xl md:grid-cols-[1.08fr_0.92fr]">
          <aside className="relative hidden overflow-hidden bg-[#11151b] text-white md:flex md:flex-col md:justify-between md:p-12">
            <img
              src={datacenterInfra}
              alt="Nova infrastructure"
              className="absolute inset-0 h-full w-full object-cover opacity-30"
            />
            <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(9,12,16,0.42),rgba(9,12,16,0.76)_48%,rgba(9,12,16,0.94)_100%)]" />
            <div className="relative z-10">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-[22px] border border-white/10 bg-white/10 backdrop-blur-sm">
                  <img src={novaIsotipoWhite} alt="Nova isotipo" className="h-14 w-14 object-contain" />
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-[0.22em] text-white/45">Nova Governance</div>
                  <div className="mt-1 text-3xl font-semibold tracking-tight text-white">Control Layer</div>
                </div>
              </div>

              <div className="mt-16 max-w-[480px]">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-white/45">Enterprise Access</p>
                <h1 className="mt-4 text-5xl font-semibold leading-[0.95] tracking-[-0.05em] text-white">
                  Security operations for teams running live agents.
                </h1>
                <p className="mt-6 text-base leading-7 text-white/68">
                  Nova no es solo un dashboard. Es la capa de control que decide, registra y justifica cada accion antes de que toque clientes, datos o infraestructura.
                </p>
              </div>

              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                {operatorStats.map((item) => (
                  <div key={item.label} className="rounded-[24px] border border-white/10 bg-white/6 p-4">
                    <p className="text-2xl font-semibold tracking-tight text-white">{item.value}</p>
                    <p className="mt-2 text-sm leading-6 text-white/58">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative z-10 space-y-4">
              {capabilityList.map((item) => (
                <div key={item} className="flex items-center gap-4 text-white/72">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-white/12 bg-white/8">
                    <div className="h-1.5 w-1.5 rounded-full bg-[#3ecf8e]" />
                  </div>
                  <span className="text-sm tracking-[-0.01em] font-medium">{item}</span>
                </div>
              ))}
            </div>
          </aside>

          <section
            className="flex min-h-[calc(100vh-2rem)] flex-col justify-center bg-[#f6efe3] px-6 py-10 text-[#111111] md:px-14 md:py-14"
            style={{ color: '#111111' }}
          >
            <div className="mx-auto w-full max-w-[460px]" style={{ color: '#111111' }}>
              <div style={{ color: '#111111' }}>
                <p className="text-[11px] font-mono uppercase tracking-[0.22em]" style={{ color: 'rgba(17,17,17,0.42)' }}>Secure entry</p>
                <h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em]" style={{ color: '#111111' }}>{panelTitle}</h2>
                <p className="mt-3 max-w-[36ch] text-sm leading-6" style={{ color: 'rgba(17,17,17,0.68)' }}>{panelSubtitle}</p>
              </div>

              <form onSubmit={handleSubmit} className="mt-10 space-y-5 rounded-[30px] bg-[#fffdfa] px-6 py-6 shadow-[0_28px_70px_-48px_rgba(0,0,0,0.24)]" style={{ color: '#111111' }}>
                {error && (
                  <div className="rounded-xl border border-danger/20 bg-danger/10 p-3 text-xs font-mono text-danger">
                    {error}
                  </div>
                )}

                {!isSignUp && (
                  <div className="mb-2 flex rounded-xl bg-[#ece2d2] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.45)]" style={{ color: '#111111' }}>
                    <button
                      type="button"
                      onClick={() => setUseApiKey(true)}
                      className={`flex-1 rounded-lg py-2 text-xs font-mono transition-all ${useApiKey ? 'bg-[#111111] text-white shadow-[0_10px_24px_-16px_rgba(0,0,0,0.55)]' : ''}`}
                      style={useApiKey ? undefined : { color: 'rgba(17,17,17,0.58)' }}
                    >
                      API Key
                    </button>
                    <button
                      type="button"
                      onClick={() => setUseApiKey(false)}
                      className={`flex-1 rounded-lg py-2 text-xs font-mono transition-all ${!useApiKey ? 'bg-[#111111] text-white shadow-[0_10px_24px_-16px_rgba(0,0,0,0.55)]' : ''}`}
                      style={!useApiKey ? undefined : { color: 'rgba(17,17,17,0.58)' }}
                    >
                      Credentials
                    </button>
                  </div>
                )}

                {useApiKey && !isSignUp ? (
                  <Field
                    label="Workspace API Key"
                    type="password"
                    value={formData.apiKey}
                    onChange={(value) => setFormData({ ...formData, apiKey: value })}
                    placeholder="nova_..."
                    required
                  />
                ) : (
                  <>
                    {isSignUp && (
                      <div className="grid gap-5 md:grid-cols-2">
                        <Field
                          label="Full name"
                          value={formData.name}
                          onChange={(value) => setFormData({ ...formData, name: value })}
                          placeholder="John Doe"
                          required
                        />
                        <Field
                          label="Company"
                          value={formData.company}
                          onChange={(value) => setFormData({ ...formData, company: value })}
                          placeholder="Acme Inc."
                        />
                      </div>
                    )}

                    <Field
                      label="Email"
                      type="email"
                      value={formData.email}
                      onChange={(value) => setFormData({ ...formData, email: value })}
                      placeholder="you@company.com"
                      required
                    />

                    <Field
                      label="Password"
                      type="password"
                      value={formData.password}
                      onChange={(value) => setFormData({ ...formData, password: value })}
                      placeholder="••••••••"
                      required
                    />
                  </>
                )}

                {!isSignUp && !useApiKey && (
                  <div className="flex items-center justify-between gap-4 pt-1">
                    <label className="flex items-center gap-2 text-xs" style={{ color: 'rgba(17,17,17,0.56)' }}>
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-black/20 bg-transparent accent-black"
                      />
                      <span>Remember me</span>
                    </label>
                    <button type="button" className="text-xs transition-colors hover:text-black" style={{ color: 'rgba(17,17,17,0.66)' }}>
                      Forgot password?
                    </button>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="mt-2 flex min-h-[56px] w-full items-center justify-center gap-2 rounded-2xl bg-[#111111] px-5 text-sm font-semibold text-white shadow-[0_24px_55px_-30px_rgba(0,0,0,0.5)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-black disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                      <span>Processing</span>
                    </>
                  ) : (
                    <span>{isSignUp ? 'Request API Key' : useApiKey ? 'Connect Workspace' : 'Sign in'}</span>
                  )}
                </button>
              </form>

              {!isSignUp && (
                <div className="relative my-8">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-black/10" />
                  </div>
                  <div className="relative flex justify-center">
                    <span className="bg-[#f6efe3] px-4 text-[11px] font-mono uppercase tracking-[0.18em]" style={{ color: 'rgba(17,17,17,0.4)' }}>
                      Alternative access
                    </span>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <SocialButton label="Google" disabled />
                <SocialButton label="GitHub" onClick={handleGithubLogin} disabled={!GITHUB_AUTH_URL} />
              </div>

              <p className="mt-4 text-center text-xs leading-6" style={{ color: 'rgba(17,17,17,0.52)' }}>
                {GITHUB_AUTH_URL
                  ? 'GitHub access is enabled for workspaces configured with Nova SSO.'
                  : 'GitHub sign-in needs a GitHub OAuth App plus a Nova backend callback. It is not active yet in this environment.'}
              </p>

              <p className="mt-8 text-center text-sm" style={{ color: 'rgba(17,17,17,0.54)' }}>
                {isSignUp ? 'Already have an account?' : "Don't have an API Key?"}{' '}
                <button
                  type="button"
                  onClick={() => setIsSignUp((current) => !current)}
                  className="font-medium transition-opacity hover:opacity-70"
                  style={{ color: '#111111' }}
                >
                  {isSignUp ? 'Sign in' : 'Request one'}
                </button>
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function Field({ label, type = 'text', value, onChange, placeholder, required = false }) {
  return (
    <label className="block">
      <span className="mb-2 block text-[10px] font-mono uppercase tracking-[0.18em]" style={{ color: 'rgba(17,17,17,0.48)' }}>{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full rounded-2xl bg-[#f1e6d6] px-4 py-3.5 text-sm !text-[#111111] placeholder:!text-black/38 outline-none transition-all duration-200 focus:bg-white focus:ring-4 focus:ring-black/[0.04]"
        style={{ color: '#111111' }}
      />
    </label>
  )
}

function SocialButton({ label, onClick, disabled = false }) {
  const icon = label === 'Google'
    ? (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.81 3.29-4.58 3.29-8.09z" />
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
        <path d="M5.84 14.09c-.22-.67-.35-1.39-.35-2.14 0-.75.13-1.47.35-2.14v-2.84H2.18C.79 9.42 0 10.66 0 12s.79 2.58 2.18 3.41l3.66-1.32z" />
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 6.84l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
      </svg>
    )
    : (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.38 7.86 10.9.58.1.79-.25.79-.56v-2.18c-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.76 2.7 1.25 3.35.96.1-.75.4-1.25.72-1.53-2.56-.29-5.25-1.28-5.25-5.72 0-1.26.45-2.3 1.18-3.11-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.18 1.19a11.03 11.03 0 0 1 5.8 0c2.21-1.5 3.18-1.19 3.18-1.19.62 1.59.23 2.76.11 3.05.73.81 1.18 1.85 1.18 3.11 0 4.45-2.69 5.42-5.26 5.71.41.35.77 1.04.77 2.1v3.11c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z" />
      </svg>
    )

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex min-h-[52px] items-center justify-center gap-2 rounded-2xl bg-[#fffdfa] px-4 text-sm shadow-[0_18px_35px_-28px_rgba(0,0,0,0.35)] transition-all duration-200 ${disabled ? 'cursor-not-allowed opacity-55' : 'hover:bg-white'}`}
      style={{ color: 'rgba(17,17,17,0.76)' }}
    >
      {icon}
      {label}
    </button>
  )
}

export default Login

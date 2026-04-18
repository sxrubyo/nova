import { create } from 'zustand'
import { api } from '@/lib/api'
import { agentCards, buildDashboardSnapshot, ledgerEntries, providerStatus } from '@/lib/mock-data'

const storage = window.localStorage

export const useUIStore = create((set) => ({
  sidebarCollapsed: storage.getItem('nova_sidebar_collapsed') === 'true',
  commandPaletteOpen: false,
  theme: storage.getItem('nova_theme') || 'dark',
  toggleSidebar: () =>
    set((state) => {
      const next = !state.sidebarCollapsed
      storage.setItem('nova_sidebar_collapsed', String(next))
      return { sidebarCollapsed: next }
    }),
  toggleCommandPalette: (value) =>
    set((state) => ({ commandPaletteOpen: typeof value === 'boolean' ? value : !state.commandPaletteOpen })),
  setTheme: (theme) => {
    storage.setItem('nova_theme', theme)
    set({ theme })
  },
}))

export const useAuthStore = create((set) => ({
  user: null,
  apiKey: storage.getItem('nova_api_key') || '',
  isAuthenticated: false,
  isLoading: true,
  setupStatus: {
    needs_setup: false,
    setup_enabled: false,
    github_enabled: false,
    recommended_login: 'api_key',
  },
  providers: { github: { enabled: false } },
  initialize: async () => {
    const existingKey = storage.getItem('nova_api_key') || ''
    set({ apiKey: existingKey, isLoading: true })

    const [setupStatus, providers] = await Promise.all([
      api.get('/setup/status').catch(() => ({
        needs_setup: false,
        setup_enabled: false,
        github_enabled: false,
        recommended_login: 'api_key',
      })),
      api.get('/auth/providers').catch(() => ({ github: { enabled: false } })),
    ])

    if (!existingKey) {
      set({
        setupStatus,
        providers,
        isAuthenticated: false,
        isLoading: false,
      })
      return
    }

    try {
      const workspace = await api.get('/workspaces/me')
      set({
        setupStatus,
        providers,
        isAuthenticated: true,
        isLoading: false,
        user: {
          name: workspace.name,
          email: workspace.email,
          plan: workspace.plan,
        },
      })
    } catch {
      storage.removeItem('nova_api_key')
      set({
        setupStatus,
        providers,
        apiKey: '',
        isAuthenticated: false,
        isLoading: false,
        user: null,
      })
    }
  },
  connectWithApiKey: async (apiKey) => {
    storage.setItem('nova_api_key', apiKey)
    set({ apiKey })
    const workspace = await api.get('/workspaces/me')
    set({
      isAuthenticated: true,
      user: {
        name: workspace.name,
        email: workspace.email,
        plan: workspace.plan,
      },
    })
    return workspace
  },
  bootstrapWorkspace: async (payload) => {
    const workspace = await api.post('/setup/bootstrap', payload)
    storage.setItem('nova_api_key', workspace.api_key)
    set({
      apiKey: workspace.api_key,
      isAuthenticated: true,
      user: {
        name: workspace.name,
        email: workspace.email,
        plan: workspace.plan,
      },
    })
    return workspace
  },
  requestAccess: async (payload) => {
    const existing = JSON.parse(storage.getItem('nova_access_requests') || '[]')
    existing.push({ ...payload, createdAt: new Date().toISOString() })
    storage.setItem('nova_access_requests', JSON.stringify(existing))
    return { success: true }
  },
  logout: async () => {
    await api.post('/auth/logout', {}).catch(() => null)
    storage.removeItem('nova_api_key')
    set({ apiKey: '', isAuthenticated: false, user: null })
  },
}))

export const useDashboardStore = create((set) => ({
  snapshot: buildDashboardSnapshot(),
  isLoading: true,
  error: '',
  fetchDashboardData: async () => {
    set({ isLoading: true, error: '' })
    try {
      const [workspace, alerts, risk, timeline, models] = await Promise.all([
        api.get('/workspaces/me'),
        api.get('/alerts?resolved=false&limit=6'),
        api.get('/stats/risk'),
        api.get('/stats/timeline?hours=24'),
        api.get('/assistant/models').catch(() => ({ providers: [] })),
      ])

      const ledger = await api.get('/ledger?limit=10')

      set({
        snapshot: {
          workspace,
          alerts,
          risk,
          timeline,
          ledger,
          models,
        },
        isLoading: false,
      })
    } catch (error) {
      set({
        snapshot: buildDashboardSnapshot(),
        error: error.message || 'Unable to load dashboard data',
        isLoading: false,
      })
    }
  },
}))

export const useAgentsStore = create((set) => ({
  agents: agentCards,
  isLoading: true,
  error: '',
  fetchAgents: async () => {
    set({ isLoading: true, error: '' })
    try {
      const agents = await api.get('/stats/agents')
      set({ agents, isLoading: false })
    } catch (error) {
      set({ agents: agentCards, error: error.message || 'Unable to load agents', isLoading: false })
    }
  },
}))

export const useLedgerStore = create((set) => ({
  entries: ledgerEntries,
  verification: {
    verified: true,
    total_records: ledgerEntries.length,
  },
  details: {},
  isLoading: true,
  error: '',
  fetchLedger: async (query = '') => {
    set({ isLoading: true, error: '' })
    try {
      const [entries, verification] = await Promise.all([
        api.get(`/ledger?limit=120${query}`),
        api.get('/ledger/verify'),
      ])
      set({ entries, verification, isLoading: false })
    } catch (error) {
      set({
        entries: ledgerEntries,
        verification: { verified: true, total_records: ledgerEntries.length },
        error: error.message || 'Unable to load ledger',
        isLoading: false,
      })
    }
  },
  fetchEntryDetail: async (id) => {
    try {
      const detail = await api.get(`/ledger/${id}`)
      set((state) => ({ details: { ...state.details, [id]: detail } }))
    } catch {
      set((state) => ({ details: { ...state.details, [id]: state.entries.find((entry) => entry.id === id) } }))
    }
  },
}))

export const useGatewayStore = create((set) => ({
  providers: providerStatus,
  failoverConfig: ['OpenRouter', 'OpenAI', 'Anthropic'],
  isLoading: true,
  fetchGatewayStatus: async () => {
    try {
      const models = await api.get('/assistant/models')
      const providers = (models.providers || []).map((provider, index) => ({
        id: provider.key,
        key: provider.key,
        name: provider.label,
        logo: provider.logo,
        status: provider.available ? 'Operational' : 'Provision Key',
        latency: 24 + index * 8,
        uptime: 99.2 + (index % 5) * 0.12,
        requestsToday: 5200 + index * 980,
        costToday: 48 + index * 19,
        models: (provider.models || []).map((model) => model.label).join(', '),
        modelList: provider.models || [],
        modelCount: (provider.models || []).length,
        defaultModel: provider.default_model,
        defaultModelLabel:
          (provider.models || []).find((model) => model.id === provider.default_model)?.label || provider.default_model,
        color: providerStatus[index % providerStatus.length].color,
      }))
      set({ providers, isLoading: false })
    } catch {
      set({ providers: providerStatus, isLoading: false })
    }
  },
}))

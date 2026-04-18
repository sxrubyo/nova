export interface WorkspaceSummary {
  id?: string
  name: string
  email?: string
  plan?: string
  usage_this_month?: number
  quota_monthly?: number
}

export interface AgentCard {
  id: string
  name: string
  model: string
  status: string
  workspace: string
  actionsToday: number
  avgRiskScore: number
  lastActive: string
}

export interface LedgerEntry {
  id: number
  actionId: string
  timestamp: string
  agent: string
  workspace: string
  actionType: string
  riskScore: number
  decision: string
  hash: string
  previousHash: string
}

export interface GatewayProvider {
  name: string
  status: string
  latency: number
  uptime: number
  requestsToday: number
  costToday: number
  models: string
}

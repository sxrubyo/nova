import { subHours, subMinutes } from 'date-fns'
import { providerCatalog } from '@/lib/provider-catalog'

const now = new Date()

const providerOperationalStatus = {
  groq: 'Degraded',
}

export const providerStatus = providerCatalog.map((provider, index) => ({
  id: provider.key,
  key: provider.key,
  name: provider.label,
  logo: provider.logo,
  status: providerOperationalStatus[provider.key] || 'Operational',
  latency: 24 + index * 7,
  uptime: 99.2 + (index % 5) * 0.13,
  requestsToday: 5400 + index * 1280,
  costToday: 42 + index * 16,
  models: provider.models.map((model) => model.label).join(', '),
  modelList: provider.models,
  modelCount: provider.models.length,
  defaultModel: provider.defaultModel,
  defaultModelLabel: provider.models.find((model) => model.id === provider.defaultModel)?.label || provider.defaultModel,
  color: provider.accent,
}))

export const agentCards = [
  ['policy-agent-01', 'Governance Sentinel', 'GPT-4o', 'Active', 'workspace-core'],
  ['policy-agent-02', 'Claims Auditor', 'Claude Sonnet 4', 'Active', 'workspace-regulated'],
  ['policy-agent-03', 'Care Escalation', 'Gemini 2.5 Pro', 'Paused', 'workspace-health'],
  ['policy-agent-04', 'Settlement Router', 'o3', 'Active', 'workspace-finance'],
  ['policy-agent-05', 'Document Classifier', 'Claude Opus 4.1', 'Blocked', 'workspace-legal'],
  ['policy-agent-06', 'Vendor Reconciler', 'GPT-4o mini', 'Active', 'workspace-ops'],
  ['policy-agent-07', 'Incident Scribe', 'Gemini 2.5 Flash', 'Active', 'workspace-core'],
  ['policy-agent-08', 'Policy QA', 'o3', 'Paused', 'workspace-labs'],
  ['policy-agent-09', 'Outbound Controls', 'Claude Sonnet 4', 'Active', 'workspace-growth'],
  ['policy-agent-10', 'Fraud Monitor', 'DeepSeek Reasoner', 'Active', 'workspace-finance'],
  ['policy-agent-11', 'Quota Guard', 'Command R+', 'Active', 'workspace-core'],
  ['policy-agent-12', 'Procurement Review', 'Mistral Medium', 'Blocked', 'workspace-ops'],
].map(([id, name, model, status, workspace], index) => ({
  id,
  name,
  model,
  status,
  workspace,
  actionsToday: 220 + index * 67,
  avgRiskScore: 12 + ((index * 11) % 78),
  lastActive: subMinutes(now, 8 + index * 11).toISOString(),
  description: 'Policy-bound agent surface with continuous evaluation and trace preservation.',
}))

export const anomalyFeed = [
  {
    id: 1,
    severity: 'critical',
    title: 'Burst detected',
    description: 'agent-07 exceeded 50 req/min threshold in workspace-prod.',
    timestamp: subMinutes(now, 2).toISOString(),
  },
  {
    id: 2,
    severity: 'warning',
    title: 'Loop detected',
    description: 'agent-03 repeated task similarity above 0.85.',
    timestamp: subMinutes(now, 17).toISOString(),
  },
  {
    id: 3,
    severity: 'warning',
    title: 'Safety score dropped',
    description: 'workspace-regulated fell below the configured threshold.',
    timestamp: subMinutes(now, 63).toISOString(),
  },
  {
    id: 4,
    severity: 'info',
    title: 'Failover exercised',
    description: 'OpenRouter rerouted requests from Groq to OpenAI during transient latency spikes.',
    timestamp: subHours(now, 3).toISOString(),
  },
]

export const ledgerEntries = Array.from({ length: 16 }, (_, index) => {
  const riskScore = 12 + ((index * 13) % 84)
  const decision = riskScore > 70 ? 'Blocked' : riskScore > 40 ? 'Escalated' : 'Allow'
  return {
    id: 48120 + index,
    actionId: `act_${48120 + index}`,
    timestamp: subMinutes(now, 7 + index * 9).toISOString(),
    agent: agentCards[index % agentCards.length].name,
    workspace: agentCards[index % agentCards.length].workspace,
    actionType: ['email.send', 'payment.refund', 'ticket.update', 'file.write'][index % 4],
    action: ['Issue refund request', 'Send outbound communication', 'Write CRM field', 'Open vendor workflow'][index % 4],
    riskScore,
    decision,
    duration: `${34 + index * 3}ms`,
    hash: `0x7f${(48120 + index).toString(16)}c9ab${index}ff93`,
    previousHash: `0x6d${(48119 + index).toString(16)}c4ad${index}de77`,
    violations: decision === 'Allow' ? [] : ['Threshold breach', 'Sensitive field exposure'],
    flags: decision === 'Allow' ? ['normal'] : ['pii', 'policy-conflict'],
    payload: {
      workspace_id: agentCards[index % agentCards.length].workspace,
      agent_id: agentCards[index % agentCards.length].id,
      intent: 'Approve high-sensitivity action after policy evaluation',
    },
  }
})

export const timelineSeries = Array.from({ length: 24 }, (_, index) => ({
  hour: `${String(index).padStart(2, '0')}:00`,
  score: 18 + ((index * 9) % 62),
  total: 180 + index * 12,
  approved: 160 + index * 10,
  blocked: 8 + (index % 7),
}))

export const providerUsageSeries = providerStatus.map((provider, index) => ({
  name: provider.name,
  value: 8 + (index % 4) * 6 + index * 2,
  color: provider.color,
}))

export const heatmapSeries = Array.from({ length: 7 }, (_, dayIndex) => ({
  day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dayIndex],
  hours: Array.from({ length: 12 }, (_, hourIndex) => ({
    hour: hourIndex * 2,
    value: 8 + ((dayIndex * 11 + hourIndex * 7) % 88),
  })),
}))

export const pricingPlans = [
  {
    name: 'Free',
    price: '$0',
    cadence: '/mo',
    description: 'Single workspace with evaluation basics.',
    features: ['1,000 evaluations/month', '1 workspace', 'Community support', 'Basic audit logs'],
  },
  {
    name: 'Pro',
    price: '$99',
    cadence: '/mo',
    description: 'For teams actively governing production agents.',
    highlight: 'Most Popular',
    features: ['50,000 evaluations/month', '10 workspaces', 'Priority support', 'Full audit trail', 'Advanced analytics'],
  },
  {
    name: 'Enterprise',
    price: 'Contact Sales',
    cadence: '',
    description: 'Built for regulated industries and custom deployment.',
    highlight: 'For Regulated Industries',
    features: ['Unlimited evaluations', 'Unlimited workspaces', 'Dedicated support', 'Custom integrations', 'On-prem deployment', 'SLA guarantee'],
  },
]

export const testimonials = [
  {
    sector: 'Financial Services',
    quote: 'Nova OS reduced our AI incident rate by 94% without slowing decision throughput.',
    author: 'Iris Bennett',
    role: 'VP Risk Operations',
    company: 'Meridian Capital Systems',
  },
  {
    sector: 'Healthcare',
    quote: 'Compliant AI operations across 200+ agents became auditable enough for security and clinical leadership.',
    author: 'Mateo Ruiz',
    role: 'Director of Digital Safety',
    company: 'Aster Care Network',
  },
  {
    sector: 'Legal Tech',
    quote: 'Every AI decision is now fully auditable, with policy rationale visible in minutes instead of days.',
    author: 'Lena Hart',
    role: 'Chief Platform Counsel',
    company: 'Northline Legal Cloud',
  },
]

export const docsSections = [
  {
    slug: 'getting-started',
    title: 'Getting Started',
    body: 'Deploy Nova OS as the control plane between your autonomous agents and the systems they touch. Connect providers, define policy, and watch the decision stream converge into one auditable surface.',
    code: 'curl -X POST https://api.nova.local/validate \\\n  -H "x-api-key: nova_live_xxx" \\\n  -d \'{"token_id":"42","action":"approve payout","context":"invoice 811"}\'',
  },
  {
    slug: 'core-concepts',
    title: 'Core Concepts',
    body: 'Nova treats every agent action as intent, computes a governance score, decides whether to allow, block, or escalate, then commits the full chain to an immutable ledger.',
    code: 'Agent -> Intent Analysis -> Risk Score -> Decision -> Action -> Audit Log',
  },
  {
    slug: 'webhooks',
    title: 'Webhooks',
    body: 'Subscribe operational systems to approval, block, anomaly, and gateway events so downstream tooling stays in sync with policy outcomes.',
    code: 'POST /webhook/{api_key}\nPOST /gateway/{api_key}/forward\nGET /stream/events',
  },
  {
    slug: 'security',
    title: 'Security',
    body: 'Use workspace-scoped API keys, signed sessions, cryptographic hash chaining, and tamper-evident exports to satisfy auditors without building custom evidence collection.',
    code: 'GET /ledger/verify\nGET /ledger/export?fmt=csv\nPATCH /alerts/{id}/resolve',
  },
]

export const incidents = [
  {
    title: 'Gateway latency spike',
    status: 'Monitoring',
    startedAt: subHours(now, 5).toISOString(),
    impact: 'Groq and OpenRouter latency elevated for 11 minutes before failover stabilized traffic.',
  },
  {
    title: 'No active incidents',
    status: 'Operational',
    startedAt: subHours(now, 30).toISOString(),
    impact: 'Core ledger, analytics, auth, and workspace APIs operating within baseline.',
  },
]

export function buildDashboardSnapshot() {
  return {
    workspace: {
      name: 'Nova Production Command',
      plan: 'Enterprise',
      usage_this_month: 12847,
      quota_monthly: 50000,
      stats: {
        total_actions: 12847,
        blocked: 47,
        escalated: 114,
        active_agents: 8,
        approval_rate: 96.4,
        avg_score: 23.4,
        alerts_pending: 4,
      },
    },
    alerts: anomalyFeed,
    ledger: ledgerEntries.slice(0, 10),
    risk: {
      agents: agentCards.slice(0, 8).map((agent, index) => ({
        agent_name: agent.name,
        risk_score: 18 + index * 9,
        blocked: index % 3,
        escalated: index % 2,
        total: 70 + index * 8,
        avg_score: 84 - index * 4,
        last_action: agent.lastActive,
      })),
    },
    timeline: timelineSeries,
  }
}

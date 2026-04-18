import {
  Activity,
  AlertTriangle,
  BookOpen,
  Building2,
  Cpu,
  Database,
  FolderKanban,
  Gauge,
  Home,
  Layers3,
  Router,
  Settings2,
  Shield,
  Wifi,
} from 'lucide-react'

export const APP_NAME = 'Nova OS'
export const APP_VERSION = '4.0.0'
export const APP_TITLE = 'Nova OS - AI Governance & Control Platform'
export const APP_DESCRIPTION =
  'The governance layer for autonomous AI agents. Intent analysis, risk scoring, cryptographic audit trails, and multi-LLM orchestration for enterprise.'

export const PUBLIC_NAV = [
  { label: 'Platform', href: '#platform' },
  { label: 'Architecture', href: '#architecture' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Documentation', href: '/docs' },
  { label: 'Status', href: '/status' },
]

export const DASHBOARD_NAV = [
  { label: 'Dashboard', href: '/dashboard', icon: Home },
  { label: 'Agents', href: '/dashboard/agents', icon: Cpu },
  { label: 'Workspaces', href: '/dashboard/workspaces', icon: FolderKanban },
  { label: 'Intent Ledger', href: '/dashboard/ledger', icon: BookOpen },
  { label: 'Risk Analytics', href: '/dashboard/analytics', icon: Gauge },
  { label: 'Memory Explorer', href: '/dashboard/memory', icon: Database },
  { label: 'Gateway Status', href: '/dashboard/gateway', icon: Wifi },
  { label: 'Anomaly Monitor', href: '/dashboard/anomalies', icon: AlertTriangle },
  { label: 'Settings', href: '/dashboard/settings', icon: Settings2 },
]

export const PUBLIC_FOOTER_COLUMNS = [
  {
    title: 'Product',
    links: ['Overview', 'Intent Analysis Engine', 'Cryptographic Ledger', 'Gateway Status'],
  },
  {
    title: 'Resources',
    links: ['Documentation', 'API Reference', 'Status Page', 'Security'],
  },
  {
    title: 'Company',
    links: ['About', 'Careers', 'Contact', 'Press'],
  },
  {
    title: 'Legal',
    links: ['Privacy', 'Terms', 'Compliance', 'Trust Center'],
  },
]

export const HERO_METRICS = [
  { label: '99.97% uptime SLA', value: 99.97, suffix: '%' },
  { label: '<50ms decision latency', value: 47, suffix: 'ms' },
  { label: 'LLM providers supported', value: 9, suffix: '' },
  { label: 'Action auditability', value: 100, suffix: '%' },
]

export const ARCHITECTURE_FLOW = [
  { id: 'agent', title: 'Agent', accent: 'accent-2' },
  { id: 'intent', title: 'Intent Analysis', accent: 'accent' },
  { id: 'risk', title: 'Risk Score', accent: 'info' },
  { id: 'decision', title: 'Allow / Block / Escalate', accent: 'warning' },
  { id: 'action', title: 'Action Execution', accent: 'success' },
  { id: 'audit', title: 'Audit Log', accent: 'accent' },
]

export const FEATURE_ICONS = {
  shield: Shield,
  anomaly: Activity,
  memory: Layers3,
  controls: Building2,
  router: Router,
}

import { useMemo } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { Area, AreaChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, ArrowUpRight, Cpu, ShieldCheck, Zap } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import ProviderMark from '@/components/brand/ProviderMark'
import { Card, CardContent, CardHeader, Badge, SparkLine, StatusDot, DecisionBadge } from '@/components/ui'
import { useDashboard } from '@/hooks/useDashboard'
import { providerStatus, providerUsageSeries } from '@/lib/mock-data'
import { formatCompactNumber, formatNumber, formatRelativeTime } from '@/lib/utils'

function DashboardOverview() {
  const shell = useOutletContext()
  const { snapshot, isLoading, error } = useDashboard()
  const stats = snapshot.workspace?.stats || snapshot.workspace?.stats || {}
  const timeline = useMemo(
    () =>
      (snapshot.timeline || []).map((row) => ({
        hour: row.hour?.slice?.(11, 16) || row.hour,
        score: row.avg_score || row.score || 0,
        total: row.total || 0,
        approved: row.approved || 0,
        blocked: row.blocked || 0,
      })),
    [snapshot.timeline],
  )

  const ledgers = snapshot.ledger || []
  const alerts = snapshot.alerts || []
  const connectedAgents = shell?.discovery?.connectedAgents || []
  const discoveryEvents = (shell?.events || []).filter((event) => ['agent_discovered', 'agent_connected', 'agent_lost'].includes(event.type)).slice(0, 4)

  const kpis = [
    {
      title: 'Actions Evaluated Today',
      value: stats.total_actions || snapshot.workspace?.usage_this_month || 12847,
      subtitle: 'With governed approval traces',
      icon: ShieldCheck,
      spark: [12, 16, 18, 24, 22, 27, 32],
    },
    {
      title: 'Average Risk Score',
      value: stats.avg_score || 23.4,
      subtitle: 'Green operating window',
      icon: Zap,
      spark: [32, 30, 28, 27, 25, 24, 23],
    },
    {
      title: 'Blocked Actions',
      value: stats.blocked || 47,
      subtitle: 'Policy prevented execution',
      icon: AlertTriangle,
      spark: [4, 6, 5, 9, 7, 8, 11],
    },
    {
      title: 'Active Agents',
      value: `${stats.active_agents || 8}/12`,
      subtitle: 'Runtime agents online',
      icon: Cpu,
      spark: [5, 6, 6, 7, 8, 8, 8],
    },
  ]

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Bridge View"
        title="The control center for governed agent operations"
        description="Track live decisions, risk movement, anomalies, and provider health from one dense but readable surface."
      />

      {error && <div className="rounded-[24px] border border-nova-warning/20 bg-nova-warning/12 px-5 py-4 text-sm text-nova-warning">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card variant="glass">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Connected Agents</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Live control lanes</div>
            </div>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            {connectedAgents.length === 0 ? (
              <div className="rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] px-4 py-5 text-sm text-nova-text-secondary">
                No connected agents yet. <Link to="/dashboard/discover" className="text-white">Discover agents</Link>
              </div>
            ) : (
              connectedAgents.map((agent) => (
                <Link key={agent.agent_key} to={`/dashboard/agents/${agent.metadata?.connected_agent_id}`} className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4 transition hover:border-white/20 hover:bg-white/[0.05]">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium text-white">{agent.name}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.18em] text-nova-text-secondary">{agent.type}</div>
                    </div>
                    <StatusDot tone={agent.is_running ? 'success' : 'gray'} pulse={agent.is_running} />
                  </div>
                  <div className="mt-4 text-sm text-nova-text-secondary">Risk baseline <span className="text-white">{agent.risk_profile?.base_risk || 0}</span></div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        <Card variant="glass">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Discovery Alerts</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Host runtime changes</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {discoveryEvents.length === 0 ? (
              <div className="rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] px-4 py-5 text-sm text-nova-text-secondary">
                Waiting for discovery events from the live feed.
              </div>
            ) : (
              discoveryEvents.map((event, index) => (
                <div key={`${event.timestamp}-${index}`} className="rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-4">
                  <div className="flex items-center justify-between gap-4">
                    <div className="text-sm font-medium text-white">{event.type.replaceAll('_', ' ')}</div>
                    <div className="text-xs text-nova-text-secondary">{formatRelativeTime(event.timestamp)}</div>
                  </div>
                  <div className="mt-2 text-sm text-nova-text-secondary">{event.payload?.name || event.payload?.agent_key}</div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <Card key={kpi.title} variant="interactive">
            <CardHeader>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
                <kpi.icon className="h-5 w-5 text-nova-accent-2" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">{kpi.title}</div>
              <div className="mt-4 flex items-end justify-between gap-4">
                <div className="font-display text-4xl font-semibold tracking-[-0.06em] text-white">
                  {typeof kpi.value === 'number' ? formatNumber(kpi.value) : kpi.value}
                </div>
                <SparkLine points={kpi.spark} />
              </div>
              <div className="mt-3 text-sm text-nova-text-secondary">{kpi.subtitle}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <Card variant="elevated">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Risk Score Distribution (24h)</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Observed decision pressure</div>
            </div>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline}>
                <defs>
                  <linearGradient id="riskFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#6C5CE7" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#6C5CE7" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" stroke="#8888A0" />
                <YAxis stroke="#8888A0" />
                <Tooltip contentStyle={{ background: '#12121A', border: '1px solid #2A2A3E', borderRadius: 18 }} />
                <Area type="monotone" dataKey="score" stroke="#7C6CF7" fill="url(#riskFill)" strokeWidth={3} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card variant="elevated">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Actions by Provider</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Gateway distribution</div>
            </div>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={providerUsageSeries} dataKey="value" innerRadius={72} outerRadius={108} paddingAngle={3}>
                  {providerUsageSeries.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#12121A', border: '1px solid #2A2A3E', borderRadius: 18 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {providerUsageSeries.slice(0, 6).map((provider) => (
                <div key={provider.name} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs">
                  <div className="flex items-center gap-2 text-white">
                    <StatusDot tone="info" />
                    {provider.name}
                  </div>
                  <div className="text-nova-text-secondary">{provider.value}%</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Recent Intent Evaluations</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Latest runtime decisions</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {ledgers.slice(0, 10).map((entry) => (
              <div key={entry.id || entry.actionId} className="grid gap-3 rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-4 lg:grid-cols-[1.1fr_1fr_130px_110px]">
                <div>
                  <div className="font-medium text-white">{entry.agent_name || entry.agent}</div>
                  <div className="mt-1 text-sm text-nova-text-secondary">{entry.action || entry.actionType}</div>
                </div>
                <div className="text-sm text-nova-text-secondary">{formatRelativeTime(entry.executed_at || entry.timestamp)}</div>
                <div className="text-sm text-white">{entry.score || entry.riskScore}</div>
                <div className="flex justify-start lg:justify-end">
                  <DecisionBadge value={entry.verdict || entry.decision} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Anomaly Alerts</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Operator feed</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {alerts.map((alert) => (
              <div key={alert.id} className="rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <StatusDot tone={alert.severity === 'critical' ? 'danger' : alert.severity === 'warning' ? 'warning' : 'info'} pulse />
                    <div className="text-sm font-medium text-white">{alert.title || alert.message}</div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-nova-text-muted" />
                </div>
                <div className="mt-3 text-sm leading-7 text-nova-text-secondary">{alert.description || alert.message}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card variant="elevated">
        <CardHeader>
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">System Health</div>
            <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Provider status and failover readiness</div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {providerStatus.map((provider) => (
            <div key={provider.name} className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-start gap-3">
                  <ProviderMark
                    src={provider.logo}
                    alt={`${provider.name} logo`}
                    frameClassName="h-12 w-12 rounded-[16px] p-2.5"
                    imageClassName="max-h-6 max-w-6"
                  />
                  <div>
                    <div className="text-sm font-medium text-white">{provider.name}</div>
                    <div className="mt-1 text-xs text-nova-text-secondary">{provider.defaultModelLabel}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-nova-text-secondary">
                  <StatusDot tone={provider.status === 'Degraded' ? 'warning' : 'success'} pulse />
                  {provider.status}
                </div>
              </div>
              <div className="mt-4 text-3xl font-semibold tracking-[-0.05em] text-white">{provider.latency}ms</div>
              <div className="mt-2 text-sm text-nova-text-secondary">{formatCompactNumber(provider.requestsToday)} requests today</div>
            </div>
          ))}
        </CardContent>
      </Card>

      {isLoading && <div className="text-sm text-nova-text-secondary">Refreshing control plane telemetry...</div>}
    </div>
  )
}

export default DashboardOverview

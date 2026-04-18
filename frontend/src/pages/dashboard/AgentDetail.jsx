import { useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext, useParams } from 'react-router-dom'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Pause, Play, RefreshCcw, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { PageHeader } from '@/components/PageHeader'
import { Badge, Button, Card, CardContent, CardHeader, Input, Table, TabsContent, TabsList, TabsRoot, TabsTrigger } from '@/components/ui'
import { api } from '@/lib/api'
import { formatDateTime, formatRelativeTime } from '@/lib/utils'

function AgentDetail() {
  const { id } = useParams()
  const shell = useOutletContext()
  const discoveryAgent = shell.discovery.agents.find((agent) => agent.metadata?.connected_agent_id === id) || null
  const [agent, setAgent] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState(null)
  const [streamMetrics, setStreamMetrics] = useState(null)
  const [query, setQuery] = useState('')
  const [editableMetadata, setEditableMetadata] = useState(null)

  useEffect(() => {
    const load = async () => {
      const [agentResponse, metricsResponse, logsResponse] = await Promise.all([
        api.get(`/agents/${id}`),
        api.get(`/agents/${id}/metrics`).catch(() => null),
        api.get(`/agents/${id}/logs`).catch(() => []),
      ])
      setAgent(agentResponse)
      setMetrics(metricsResponse)
      setLogs(logsResponse)
      setEditableMetadata(agentResponse.metadata || {})
      if (discoveryAgent) {
        const nextStatus = await shell.discovery.getAgentStatus(discoveryAgent.agent_key)
        setStatus(nextStatus)
      }
    }
    load()
  }, [id, discoveryAgent, shell.discovery])

  useEffect(() => {
    const source = new EventSource(`/api/agents/${id}/stream`)
    source.onmessage = (event) => {
      try {
        setStreamMetrics(JSON.parse(event.data))
      } catch {
        // Ignore malformed payloads.
      }
    }
    return () => source.close()
  }, [id])

  const timeline = useMemo(
    () => (metrics?.actions_per_hour || []).map((item) => ({ hour: item.hour?.slice?.(11, 16) || item.hour, count: item.count })),
    [metrics],
  )

  const filteredLogs = logs.filter((log) => JSON.stringify(log).toLowerCase().includes(query.toLowerCase()))
  const liveEvents = shell.events.filter((event) => event.payload?.agent_id === id).slice(0, 20)

  const savePolicy = async () => {
    await api.put(`/agents/${id}`, { metadata: editableMetadata })
    toast.success('Agent policy updated')
  }

  const runDiscoveryAction = async (action) => {
    if (!discoveryAgent) return
    await api.post(`/discovery/agents/${discoveryAgent.agent_key}/${action}`, {})
    toast.success(`Agent ${action} signal sent`)
  }

  if (!agent) {
    return <div className="text-sm text-nova-text-secondary">Loading agent detail...</div>
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Agent Detail"
        title={agent.name}
        description="Inspect health, live metrics, logs, connection metadata, and runtime policy in one surface."
        action={
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={status?.health?.ok ? 'success' : 'warning'} dot>
              {status?.health?.ok ? 'Online' : agent.status}
            </Badge>
            <Button variant="outline" onClick={() => runDiscoveryAction('pause')}><Pause className="h-4 w-4" /> Pause</Button>
            <Button variant="outline" onClick={() => runDiscoveryAction('resume')}><Play className="h-4 w-4" /> Resume</Button>
            <Button variant="secondary" onClick={() => discoveryAgent && shell.discovery.connectAgent(discoveryAgent.agent_key)}><RefreshCcw className="h-4 w-4" /> Reconnect</Button>
          </div>
        }
      />

      <div className="grid gap-5 md:grid-cols-4">
        <StatCard label="Actions today" value={streamMetrics?.actions_count || metrics?.actions_per_hour?.reduce((sum, item) => sum + item.count, 0) || 0} />
        <StatCard label="Avg risk score" value={streamMetrics?.risk_score || metrics?.avg_risk_score || 0} />
        <StatCard label="Blocked rate" value={`${streamMetrics?.blocked_rate || metrics?.blocked_rate || 0}%`} />
        <StatCard label="Response avg" value={`${streamMetrics?.response_time_avg || metrics?.response_time_avg || 0} ms`} />
      </div>

      <TabsRoot defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="live">Live Feed</TabsTrigger>
          <TabsTrigger value="rules">Permissions & Rules</TabsTrigger>
          <TabsTrigger value="connection">Connection</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
            <Card variant="elevated">
              <CardHeader>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Activity chart</div>
                  <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Last 24 hours</div>
                </div>
              </CardHeader>
              <CardContent className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeline}>
                    <defs>
                      <linearGradient id="agentActivity" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#00D4AA" stopOpacity={0.46} />
                        <stop offset="100%" stopColor="#00D4AA" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="hour" stroke="#8888A0" />
                    <YAxis stroke="#8888A0" />
                    <Tooltip contentStyle={{ background: '#12121A', border: '1px solid #2A2A3E', borderRadius: 18 }} />
                    <Area type="monotone" dataKey="count" stroke="#00D4AA" fill="url(#agentActivity)" strokeWidth={3} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card variant="elevated">
              <CardHeader>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Agent summary</div>
                  <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Assigned runtime</div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <SummaryRow label="Provider" value={agent.provider} />
                <SummaryRow label="Model" value={agent.model} />
                <SummaryRow label="Created" value={formatDateTime(agent.created_at)} />
                <SummaryRow label="Last action" value={streamMetrics?.last_action ? formatRelativeTime(streamMetrics.last_action) : 'No recent events'} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="live">
          <Card variant="elevated">
            <CardHeader>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Realtime feed</div>
                <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Latest evaluations and runtime signals</div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {liveEvents.length === 0 ? (
                <div className="rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-5 text-sm text-nova-text-secondary">
                  Waiting for live events for this agent.
                </div>
              ) : (
                liveEvents.map((event, index) => (
                  <div key={`${event.timestamp}-${index}`} className="rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="text-sm font-medium text-white">{event.type}</div>
                      <div className="text-xs text-nova-text-secondary">{formatDateTime(event.timestamp)}</div>
                    </div>
                    <div className="mt-2 text-sm leading-7 text-nova-text-secondary">{JSON.stringify(event.payload)}</div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rules">
          <Card variant="elevated">
            <CardHeader>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Editable policy</div>
                <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Permissions and thresholds</div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <Input
                label="Allowed actions"
                value={(editableMetadata?.permissions?.can_do || []).join(', ')}
                onChange={(event) => setEditableMetadata((current) => ({
                  ...current,
                  permissions: {
                    ...(current?.permissions || {}),
                    can_do: event.target.value.split(',').map((item) => item.trim()).filter(Boolean),
                  },
                }))}
              />
              <Input
                label="Blocked actions"
                value={(editableMetadata?.permissions?.cannot_do || []).join(', ')}
                onChange={(event) => setEditableMetadata((current) => ({
                  ...current,
                  permissions: {
                    ...(current?.permissions || {}),
                    cannot_do: event.target.value.split(',').map((item) => item.trim()).filter(Boolean),
                  },
                }))}
              />
              <div className="grid gap-4 md:grid-cols-3">
                {['auto_allow', 'escalate', 'auto_block'].map((key) => (
                  <Input
                    key={key}
                    label={key}
                    value={editableMetadata?.risk_thresholds?.[key] || ''}
                    onChange={(event) => setEditableMetadata((current) => ({
                      ...current,
                      risk_thresholds: {
                        ...(current?.risk_thresholds || {}),
                        [key]: Number(event.target.value),
                      },
                    }))}
                  />
                ))}
              </div>
              <Button onClick={savePolicy}>Save changes</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="connection">
          <Card variant="elevated">
            <CardHeader>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Connection detail</div>
                <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Connector state</div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {!discoveryAgent ? (
                <div className="rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-nova-text-secondary">
                  This managed agent does not map to a discovered host runtime yet.
                </div>
              ) : (
                <>
                  <SummaryRow label="Discovery key" value={discoveryAgent.agent_key} />
                  <SummaryRow label="Fingerprint" value={discoveryAgent.fingerprint_key} />
                  <SummaryRow label="Connector" value={status?.connector || status?.runtime?.connector || 'unknown'} />
                  <SummaryRow label="Confidence" value={`${Math.round((discoveryAgent.confidence || 0) * 100)}%`} />
                  <SummaryRow label="Detection" value={(discoveryAgent.detection_methods || []).join(' + ')} />
                  <div className="flex gap-3">
                    <Button variant="outline" onClick={() => discoveryAgent && shell.discovery.connectAgent(discoveryAgent.agent_key)}>Test connection</Button>
                    <Button variant="secondary" onClick={() => discoveryAgent && shell.discovery.refresh(true)}>Rescan host</Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card variant="elevated">
            <CardHeader>
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Searchable logs</div>
                <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Execution history</div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter logs..." />
              <Table
                columns={[
                  { key: 'created_at', label: 'Timestamp', render: (row) => formatDateTime(row.created_at) },
                  { key: 'action', label: 'Action' },
                  { key: 'decision', label: 'Decision', render: (row) => <Badge variant={row.decision === 'BLOCK' ? 'danger' : row.decision === 'ESCALATE' ? 'warning' : 'success'}>{row.decision}</Badge> },
                  { key: 'risk_score', label: 'Risk' },
                  { key: 'status', label: 'Status' },
                ]}
                data={filteredLogs}
                emptyTitle="No logs found"
                emptyDescription="This agent has no ledger-backed executions yet."
              />
            </CardContent>
          </Card>
        </TabsContent>
      </TabsRoot>

      <div className="text-sm text-nova-text-secondary">
        <Link to="/dashboard/agents" className="inline-flex items-center gap-2 hover:text-white">
          <ShieldCheck className="h-4 w-4" />
          Back to agents
        </Link>
      </div>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-white/[0.03] p-5">
      <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">{label}</div>
      <div className="mt-4 text-3xl font-semibold tracking-[-0.05em] text-white">{value}</div>
    </div>
  )
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex items-center justify-between rounded-[22px] border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="text-sm text-nova-text-secondary">{label}</div>
      <div className="max-w-[60%] text-right text-sm text-white">{value}</div>
    </div>
  )
}

export default AgentDetail

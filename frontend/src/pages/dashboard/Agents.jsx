import { useMemo, useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import { Pause, Search, Settings2, ShieldCheck } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { Badge, Button, Card, CardContent, CardFooter, CardHeader, Input, RiskGauge, SelectField } from '@/components/ui'
import { useAgents } from '@/hooks/useAgents'
import { formatRelativeTime } from '@/lib/utils'

function normalizeAgent(agent, index) {
  if (agent.id) return agent
  const status = (agent.blocked || 0) > 0 ? 'Blocked' : (agent.escalated || 0) > 0 ? 'Paused' : 'Active'
  return {
    id: `agent-${index}`,
    name: agent.agent_name,
    model: ['GPT-4o', 'Claude Sonnet 4', 'Gemini 2.5 Pro', 'o3'][index % 4],
    status,
    workspace: ['workspace-core', 'workspace-regulated', 'workspace-finance'][index % 3],
    actionsToday: agent.total_actions,
    avgRiskScore: 100 - (agent.avg_score || 0),
    lastActive: agent.last_action,
    description: 'Governed runtime agent with assigned model policy and workspace scope.',
  }
}

function DashboardAgents() {
  const navigate = useNavigate()
  const shell = useOutletContext()
  const { agents, isLoading } = useAgents()
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [workspace, setWorkspace] = useState('all')
  const normalized = useMemo(() => agents.map(normalizeAgent), [agents])
  const connectedIds = new Set((shell?.discovery?.connectedAgents || []).map((agent) => agent.metadata?.connected_agent_id))

  const filtered = normalized.filter((agent) => {
    const textMatch = `${agent.name} ${agent.model}`.toLowerCase().includes(query.toLowerCase())
    const statusMatch = status === 'all' || agent.status.toLowerCase() === status
    const workspaceMatch = workspace === 'all' || agent.workspace === workspace
    return textMatch && statusMatch && workspaceMatch
  })

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Agent Registry"
        title="Governed agents mapped to operational workspaces"
        description="Search, filter, and act on the agents currently running under Nova policies."
        action={<Button onClick={() => navigate('/dashboard/agents/new')}>Register New Agent</Button>}
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_180px_220px]">
        <Input icon={Search} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by agent or model" />
        <SelectField value={status} onValueChange={setStatus} options={[{ value: 'all', label: 'All statuses' }, { value: 'active', label: 'Active' }, { value: 'paused', label: 'Paused' }, { value: 'blocked', label: 'Blocked' }]} />
        <SelectField value={workspace} onValueChange={setWorkspace} options={[{ value: 'all', label: 'All workspaces' }, ...Array.from(new Set(normalized.map((agent) => agent.workspace))).map((name) => ({ value: name, label: name }))]} />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        {filtered.map((agent) => (
          <Card key={agent.id} variant="interactive">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
                  <ShieldCheck className="h-5 w-5 text-nova-accent-2" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-white">{agent.name}</div>
                  <div className="mt-1 text-xs uppercase tracking-[0.18em] text-nova-text-secondary">{agent.id}</div>
                </div>
              </div>
              <Badge variant={agent.status === 'Blocked' ? 'danger' : agent.status === 'Paused' ? 'warning' : 'success'}>
                {agent.status}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-[1fr_120px]">
                <div className="space-y-3 text-sm text-nova-text-secondary">
                  <div>Model assigned: <span className="text-white">{agent.model}</span></div>
                  <div>Workspace: <span className="text-white">{agent.workspace}</span></div>
                  <div>Actions today: <span className="text-white">{agent.actionsToday}</span></div>
                  <div>Last active: <span className="text-white">{formatRelativeTime(agent.lastActive)}</span></div>
                  <div>Discovery link: <span className="text-white">{connectedIds.has(agent.id) ? 'Connected to host runtime' : 'Registry only'}</span></div>
                </div>
                <div className="flex justify-center"><RiskGauge value={agent.avgRiskScore} size={120} /></div>
              </div>
            </CardContent>
            <CardFooter>
              <Button variant="outline" size="sm" onClick={() => navigate(`/dashboard/agents/${agent.id}`)}><Pause className="h-4 w-4" /> Pause</Button>
              <Button variant="ghost" size="sm" onClick={() => navigate(`/dashboard/agents/${agent.id}`)}><Settings2 className="h-4 w-4" /> Configure</Button>
              <Button variant="secondary" size="sm" onClick={() => navigate(`/dashboard/agents/${agent.id}`)}>View Logs</Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {isLoading && <div className="text-sm text-nova-text-secondary">Refreshing agent registry...</div>}
    </div>
  )
}

export default DashboardAgents

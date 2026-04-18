import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, Input, Badge } from '@/components/ui'
import { agentCards } from '@/lib/mock-data'

const memories = [
  { layer: 'Core', key: 'governance.baseline', value: 'Never approve high-value payouts without operator review.' },
  { layer: 'Episodic', key: 'incident.2026-03-23', value: 'Observed loop pattern in settlement router after malformed vendor callback.' },
  { layer: 'Working', key: 'today.queue', value: 'Agent-07 currently under anomaly watch with elevated burst activity.' },
]

function DashboardMemory() {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => memories.filter((memory) => `${memory.key} ${memory.value}`.toLowerCase().includes(query.toLowerCase())), [query])

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Memory Explorer" title="Context layers that agents retain between decisions" description="Audit how Nova stores persistent context and which memories continue to influence operational behavior." />
      <Input icon={Search} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search memory keys or values" />
      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <div className="text-2xl font-semibold tracking-[-0.04em] text-white">Agent selection</div>
          </CardHeader>
          <CardContent className="space-y-3">
            {agentCards.slice(0, 6).map((agent) => (
              <div key={agent.id} className="rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white">{agent.name}</div>
            ))}
          </CardContent>
        </Card>
        <div className="space-y-5">
          {filtered.map((memory) => (
            <Card key={memory.key} variant="interactive">
              <CardHeader>
                <div>
                  <Badge variant="outline">{memory.layer}</Badge>
                  <div className="mt-4 text-xl font-semibold text-white">{memory.key}</div>
                </div>
              </CardHeader>
              <CardContent className="text-sm leading-7 text-nova-text-secondary">{memory.value}</CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}

export default DashboardMemory

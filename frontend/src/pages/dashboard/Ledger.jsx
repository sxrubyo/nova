import { useMemo, useState } from 'react'
import { Download, Search } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { PageHeader } from '@/components/PageHeader'
import { Badge, Button, Card, CardContent, HashChain, Input, Table, DecisionBadge } from '@/components/ui'
import { useLedger } from '@/hooks/useLedger'
import { API_BASE_PATH, SERVER_ORIGIN } from '@/config/appConfig'
import { formatDateTime } from '@/lib/utils'

function normalizeEntry(entry) {
  return {
    id: entry.id,
    timestamp: entry.executed_at || entry.timestamp,
    agent: entry.agent_name || entry.agent,
    workspace: entry.workspace || 'workspace-core',
    actionType: entry.actionType || entry.action,
    riskScore: entry.score || entry.riskScore,
    decision: entry.verdict || entry.decision,
    hash: entry.own_hash || entry.hash,
    previousHash: entry.prev_hash || entry.previousHash,
    payload: entry.context || entry.payload,
    violations: entry.violations || entry.score_factors || {},
    flags: entry.flags || entry.risk_level || 'normal',
  }
}

function DashboardLedger() {
  const { entries, verification, details, fetchEntryDetail, isLoading, fetchLedger } = useLedger()
  const [expandedRowId, setExpandedRowId] = useState(null)
  const [query, setQuery] = useState('')
  const [decision, setDecision] = useState('all')

  const normalized = useMemo(() => entries.map(normalizeEntry), [entries])
  const filtered = normalized.filter((entry) => {
    const haystack = `${entry.agent} ${entry.actionType} ${entry.hash}`.toLowerCase()
    const matchesQuery = haystack.includes(query.toLowerCase())
    const matchesDecision = decision === 'all' || entry.decision.toLowerCase() === decision
    return matchesQuery && matchesDecision
  })

  const handleExport = async () => {
    try {
      const response = await fetch(`${SERVER_ORIGIN}${API_BASE_PATH}/ledger/export?fmt=csv&limit=1000`, {
        headers: {
          'x-api-key': localStorage.getItem('nova_api_key') || '',
        },
      })
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'nova-ledger.csv'
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Unable to export live ledger. Using current mock view.')
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Intent Ledger"
        title="Cryptographic audit trail across governed actions"
        description="Inspect action lineage, rule violations, and chain integrity without leaving the main operational surface."
        action={<Button onClick={handleExport}><Download className="h-4 w-4" /> Export CSV</Button>}
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_auto]">
        <Input icon={Search} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by action id, hash, agent, or workspace" />
        <div className="flex flex-wrap gap-2">
          {['all', 'allow', 'blocked', 'escalated'].map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setDecision(value)}
              className={`rounded-full border px-4 py-2 text-xs uppercase tracking-[0.18em] transition ${decision === value ? 'border-transparent bg-white text-[#090a0f]' : 'border-white/10 bg-white/[0.03] text-nova-text-secondary'}`}
            >
              {value}
            </button>
          ))}
        </div>
      </div>

      <Card variant="default">
        <CardContent className="pt-6">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Badge variant={verification?.verified ? 'success' : 'danger'}>
                {verification?.verified ? 'Chain verified' : 'Integrity issue'}
              </Badge>
              <div className="text-sm text-nova-text-secondary">{verification?.total_records || filtered.length} records inspected</div>
            </div>
            <HashChain entries={filtered.slice(0, 4).map((entry) => ({ label: entry.agent, hash: entry.hash || '0x000' }))} />
          </div>
          <Table
            columns={[
              { key: 'timestamp', label: 'Timestamp', render: (row) => formatDateTime(row.timestamp) },
              { key: 'agent', label: 'Agent' },
              { key: 'workspace', label: 'Workspace' },
              { key: 'actionType', label: 'Action Type' },
              { key: 'riskScore', label: 'Risk Score' },
              { key: 'decision', label: 'Decision', render: (row) => <DecisionBadge value={row.decision} /> },
              { key: 'hash', label: 'Hash', render: (row) => <span className="font-mono text-xs text-nova-text-secondary">{row.hash?.slice(0, 16)}...</span> },
            ]}
            data={filtered}
            expandedRowId={expandedRowId}
            onToggleRow={(id) => {
              const next = expandedRowId === id ? null : id
              setExpandedRowId(next)
              if (next) fetchEntryDetail(id)
            }}
            renderExpandedRow={(row) => {
              const detail = details[row.id] || row
              return (
                <div className="grid gap-5 lg:grid-cols-2">
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Payload</div>
                    <pre className="mt-3 overflow-x-auto rounded-2xl border border-white/10 bg-[#090b10] p-4 text-xs text-nova-text-primary">
                      {JSON.stringify(detail.payload || detail.context || {}, null, 2)}
                    </pre>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Rule Violations</div>
                      <div className="mt-3 text-sm text-nova-text-primary">
                        {JSON.stringify(detail.violations || detail.score_factors || detail.reason || 'No explicit rule violations')}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Previous Hash</div>
                      <div className="mt-2 font-mono text-xs text-nova-text-secondary">{detail.previousHash || detail.prev_hash || 'Unavailable'}</div>
                    </div>
                  </div>
                </div>
              )
            }}
          />
        </CardContent>
      </Card>

      {isLoading && <div className="text-sm text-nova-text-secondary">Refreshing ledger...</div>}
    </div>
  )
}

export default DashboardLedger

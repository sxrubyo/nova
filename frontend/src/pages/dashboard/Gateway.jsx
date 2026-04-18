import { PageHeader } from '@/components/PageHeader'
import { Button, Card, CardContent, CardHeader, HashChain, Badge, StatusDot } from '@/components/ui'
import ProviderMark from '@/components/brand/ProviderMark'
import { useGateway } from '@/hooks/useGateway'
import { providerStatus } from '@/lib/mock-data'
import { formatCompactNumber, formatCurrency } from '@/lib/utils'

function DashboardGateway() {
  const { providers } = useGateway()

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Gateway Status"
        title="Multi-provider routing, health, and failover visibility"
        description="Review latency, availability, spend, and routing strategy across every model provider in the Nova gateway."
        action={<Button variant="outline">Update Failover Chain</Button>}
      />

      <div className="grid gap-5 xl:grid-cols-3">
        {(providers.length ? providers : providerStatus).map((provider) => (
          <Card key={provider.name} variant="interactive">
            <CardHeader>
              <div className="flex items-start gap-3">
                <ProviderMark
                  src={provider.logo}
                  alt={`${provider.name} logo`}
                  frameClassName="h-12 w-12 rounded-[18px] p-2.5"
                  imageClassName="max-h-6 max-w-6"
                />
                <div>
                  <div className="text-xl font-semibold text-white">{provider.name}</div>
                  <div className="mt-1 text-sm text-nova-text-secondary">{provider.defaultModelLabel || provider.models}</div>
                </div>
              </div>
              <Badge variant={provider.status === 'Degraded' ? 'warning' : provider.status === 'Provision Key' ? 'outline' : 'success'}>
                {provider.status}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <Metric label="Latency" value={`${provider.latency}ms`} />
                <Metric label="Uptime" value={`${provider.uptime.toFixed(2)}%`} />
                <Metric label="Requests Today" value={formatCompactNumber(provider.requestsToday)} />
                <Metric label="Cost Today" value={formatCurrency(provider.costToday)} />
              </div>
              <div className="rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-nova-text-secondary">
                <div className="text-[11px] uppercase tracking-[0.18em]">Primary model list</div>
                <div className="mt-2 text-white">{provider.models}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Failover Chain</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Current routing order</div>
            </div>
          </CardHeader>
          <CardContent>
            <HashChain entries={(providers.length ? providers : providerStatus).slice(0, 5).map((provider) => ({ label: provider.name, hash: provider.models }))} />
          </CardContent>
        </Card>

        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Cost Optimization Suggestions</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Operator recommendations</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              'Route short-form moderation requests to Groq or GPT-4o mini to reduce blended cost.',
              'Keep Claude Sonnet reserved for escalations and policy explanation flows.',
              'Preserve OpenRouter as the top failover layer for provider outages.',
            ].map((item) => (
              <div key={item} className="flex items-start gap-3 rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-4 text-sm leading-7 text-nova-text-secondary">
                <StatusDot tone="info" pulse />
                <span>{item}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">{label}</div>
      <div className="mt-3 text-xl font-semibold text-white">{value}</div>
    </div>
  )
}

export default DashboardGateway

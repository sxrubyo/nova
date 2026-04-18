import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { NovaLogo } from '@/components/brand/NovaLogo'
import ProviderMark from '@/components/brand/ProviderMark'
import { Badge, Button, Card, CardContent, CardHeader, StatusDot } from '@/components/ui'
import { incidents, providerStatus } from '@/lib/mock-data'
import { formatRelativeTime } from '@/lib/utils'

function Status() {
  useEffect(() => {
    document.title = 'System Status | Nova OS'
  }, [])

  return (
    <div className="min-h-screen bg-[#06070b] px-4 py-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-[1440px]">
        <div className="flex items-center justify-between gap-4 rounded-[28px] border border-white/10 bg-white/[0.03] px-6 py-4">
          <NovaLogo />
          <Link to="/"><Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4" /> Site</Button></Link>
        </div>

        <div className="mt-8">
          <Badge variant="success" dot>All systems monitored</Badge>
          <h1 className="mt-6 font-display text-5xl font-semibold tracking-[-0.06em] text-white">Operational visibility across the Nova control plane</h1>
          <p className="mt-4 max-w-3xl text-lg leading-8 text-nova-text-secondary">
            Monitor service health, recent incidents, and provider behavior from one status surface aligned with the operational dashboard.
          </p>
        </div>

        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {providerStatus.map((provider) => (
            <Card key={provider.name} variant="default">
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
                <Badge variant={provider.status === 'Degraded' ? 'warning' : 'success'}>{provider.status}</Badge>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between text-sm text-nova-text-secondary">
                  <span>Latency</span>
                  <span>{provider.latency}ms</span>
                </div>
                <div className="mt-3 flex items-center justify-between text-sm text-nova-text-secondary">
                  <span>Uptime</span>
                  <span>{provider.uptime.toFixed(2)}%</span>
                </div>
                <div className="mt-4 grid grid-cols-10 gap-1">
                  {Array.from({ length: 30 }, (_, index) => (
                    <div key={index} className={`h-3 rounded-full ${index % 17 === 0 && provider.status === 'Degraded' ? 'bg-nova-warning' : 'bg-nova-success/40'}`} />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          {incidents.map((incident) => (
            <Card key={incident.title} variant="glass">
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="text-2xl font-semibold tracking-[-0.04em] text-white">{incident.title}</div>
                  <div className="flex items-center gap-2 text-sm text-nova-text-secondary">
                    <StatusDot tone={incident.status === 'Monitoring' ? 'warning' : 'success'} pulse />
                    {incident.status}
                  </div>
                </div>
                <p className="mt-4 text-sm leading-7 text-nova-text-secondary">{incident.impact}</p>
                <div className="mt-4 text-xs uppercase tracking-[0.18em] text-nova-text-muted">
                  Updated {formatRelativeTime(incident.startedAt)}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Status

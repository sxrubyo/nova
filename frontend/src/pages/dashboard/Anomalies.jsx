import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, Badge, StatusDot } from '@/components/ui'
import { anomalyFeed } from '@/lib/mock-data'
import { formatRelativeTime } from '@/lib/utils'

function DashboardAnomalies() {
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Anomaly Monitor" title="Behavioral anomalies and operator escalation feed" description="Review loops, bursts, threshold drops, and gateway stress before the workflow leaves a recoverable path." />
      <div className="space-y-4">
        {anomalyFeed.map((anomaly) => (
          <Card key={anomaly.id} variant="interactive">
            <CardHeader>
              <div className="flex items-center gap-3">
                <StatusDot tone={anomaly.severity === 'critical' ? 'danger' : anomaly.severity === 'warning' ? 'warning' : 'info'} pulse />
                <div>
                  <div className="text-2xl font-semibold tracking-[-0.04em] text-white">{anomaly.title}</div>
                  <div className="mt-2 text-sm text-nova-text-secondary">{formatRelativeTime(anomaly.timestamp)}</div>
                </div>
              </div>
              <Badge variant={anomaly.severity === 'critical' ? 'danger' : anomaly.severity === 'warning' ? 'warning' : 'info'}>
                {anomaly.severity}
              </Badge>
            </CardHeader>
            <CardContent className="text-sm leading-7 text-nova-text-secondary">{anomaly.description}</CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default DashboardAnomalies

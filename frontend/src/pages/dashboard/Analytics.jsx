import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent, CardHeader, Badge } from '@/components/ui'
import { useDashboard } from '@/hooks/useDashboard'
import { heatmapSeries, ledgerEntries, providerUsageSeries } from '@/lib/mock-data'

function DashboardAnalytics() {
  const { snapshot } = useDashboard()
  const timeline = (snapshot.timeline || []).map((row) => ({
    hour: row.hour?.slice?.(11, 16) || row.hour,
    score: row.avg_score || row.score || 0,
    total: row.total || 0,
  }))
  const highRisk = ledgerEntries
    .slice()
    .sort((left, right) => right.riskScore - left.riskScore)
    .slice(0, 10)

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Analytics" title="Risk analytics across time, agents, and sensitivity classes" description="Move beyond isolated alerts and watch how risk behaves across hours, workspaces, providers, and policy surfaces." />

      <div className="grid gap-5 xl:grid-cols-[1.06fr_0.94fr]">
        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Risk Heatmap</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Hourly concentration map</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {heatmapSeries.map((day) => (
              <div key={day.day} className="grid grid-cols-[54px_1fr] items-center gap-3">
                <div className="text-xs uppercase tracking-[0.18em] text-nova-text-secondary">{day.day}</div>
                <div className="grid grid-cols-12 gap-2">
                  {day.hours.map((slot) => (
                    <div key={`${day.day}-${slot.hour}`} className="flex h-7 items-center justify-center rounded-xl text-[10px]" style={{ background: `rgba(108, 92, 231, ${0.12 + slot.value / 120})` }}>
                      {slot.hour}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Trend Lines</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Risk by hour</div>
            </div>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline}>
                <CartesianGrid stroke="#2A2A3E" vertical={false} />
                <XAxis dataKey="hour" stroke="#8888A0" />
                <YAxis stroke="#8888A0" />
                <Tooltip contentStyle={{ background: '#12121A', border: '1px solid #2A2A3E', borderRadius: 18 }} />
                <Line type="monotone" dataKey="score" stroke="#7C6CF7" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="total" stroke="#00D4AA" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Rule Violation Frequency</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Policy pressure points</div>
            </div>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={providerUsageSeries}>
                <CartesianGrid stroke="#2A2A3E" vertical={false} />
                <XAxis dataKey="name" stroke="#8888A0" tickLine={false} axisLine={false} />
                <YAxis stroke="#8888A0" />
                <Tooltip contentStyle={{ background: '#12121A', border: '1px solid #2A2A3E', borderRadius: 18 }} />
                <Bar dataKey="value" fill="#6C5CE7" radius={[12, 12, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card variant="default">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Top 10 Highest Risk Actions</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Actions needing review</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {highRisk.map((entry) => (
              <div key={entry.id} className="rounded-[24px] border border-white/10 bg-white/[0.03] px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-sm font-medium text-white">{entry.action}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.18em] text-nova-text-secondary">{entry.agent}</div>
                  </div>
                  <Badge variant={entry.riskScore > 70 ? 'danger' : 'warning'}>{entry.riskScore}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardAnalytics

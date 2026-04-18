import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { TabsRoot, TabsList, TabsTrigger, TabsContent, Input, SelectField, SwitchField, Button, Card, CardContent } from '@/components/ui'

function DashboardSettings() {
  const [autoBlock, setAutoBlock] = useState(true)
  const [requireEscalation, setRequireEscalation] = useState(true)

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Settings" title="Workspace, security, billing, team, keys, and integrations" description="Tune the governance layer without losing sight of operational consequences." />

      <TabsRoot defaultValue="general">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
          <TabsTrigger value="keys">API Keys</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <div className="grid gap-5 xl:grid-cols-2">
            <Card><CardContent className="space-y-4">
              <Input label="Workspace name" defaultValue="Nova Production Command" />
              <SelectField label="Timezone" value="america_bogota" options={[{ value: 'america_bogota', label: 'America/Bogota' }, { value: 'utc', label: 'UTC' }]} />
              <SelectField label="Language" value="en" options={[{ value: 'en', label: 'English' }, { value: 'es', label: 'Spanish' }]} />
            </CardContent></Card>
            <Card><CardContent className="space-y-4">
              <Input label="Workspace URL" defaultValue="control.nova-os.internal" />
              <Input label="Status notifications" defaultValue="ops@northline.systems" />
              <Button>Save General Settings</Button>
            </CardContent></Card>
          </div>
        </TabsContent>

        <TabsContent value="security">
          <div className="grid gap-5 xl:grid-cols-2">
            <Card><CardContent className="space-y-4">
              <SwitchField checked={autoBlock} onCheckedChange={setAutoBlock} label="Auto-block critical actions" description="Immediately block actions above the critical threshold." />
              <SwitchField checked={requireEscalation} onCheckedChange={setRequireEscalation} label="Escalate medium-risk actions" description="Require operator review for medium-risk activities." />
              <Input label="Approved threshold" defaultValue="70" />
              <Input label="Escalate threshold" defaultValue="40" />
            </CardContent></Card>
            <Card><CardContent className="space-y-4">
              <Input label="Allowed actions" defaultValue="read.customer_profile, ticket.update, case.annotate" />
              <Input label="Denied actions" defaultValue="refund.issue_high_value, secret.read, policy.delete" />
              <Button>Update Security Rules</Button>
            </CardContent></Card>
          </div>
        </TabsContent>

        <TabsContent value="billing">
          <Card><CardContent className="grid gap-5 xl:grid-cols-3">
            <Metric title="Current plan" value="Enterprise" />
            <Metric title="Monthly usage" value="12,847 / 50,000" />
            <Metric title="Contract term" value="Annual · renews Oct 2026" />
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="team">
          <Card><CardContent className="space-y-3">
            {['Ava Salazar · Platform Security', 'Mateo Ruiz · Risk Operations', 'Lena Hart · Compliance', 'Iris Bennett · Finance Ops'].map((member) => (
              <div key={member} className="rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white">{member}</div>
            ))}
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="keys">
          <Card><CardContent className="space-y-3">
            {['nova_live_workspace_admin', 'nova_live_gateway_ops', 'nova_live_audit_export'].map((key) => (
              <div key={key} className="rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3">
                <div className="text-sm font-medium text-white">{key}</div>
                <div className="mt-1 text-xs text-nova-text-secondary">Scoped permissions with rotation every 30 days.</div>
              </div>
            ))}
            <Button>Generate New Key</Button>
          </CardContent></Card>
        </TabsContent>

        <TabsContent value="integrations">
          <Card><CardContent className="space-y-3">
            {['Slack incident channel', 'Discord anomaly alerts', 'Webhook callback URL', 'SIEM export stream'].map((item) => (
              <div key={item} className="rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white">{item}</div>
            ))}
          </CardContent></Card>
        </TabsContent>
      </TabsRoot>
    </div>
  )
}

function Metric({ title, value }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.03] px-5 py-5">
      <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">{title}</div>
      <div className="mt-4 text-2xl font-semibold text-white">{value}</div>
    </div>
  )
}

export default DashboardSettings

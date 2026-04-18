import { PageHeader } from '@/components/PageHeader'
import { Button, Card, CardContent, CardHeader, Badge, ProgressBar } from '@/components/ui'

const workspaces = [
  { name: 'workspace-core', plan: 'Enterprise', usage: 78, members: 12, region: 'us-east-1' },
  { name: 'workspace-regulated', plan: 'Enterprise', usage: 62, members: 8, region: 'eu-west-1' },
  { name: 'workspace-finance', plan: 'Pro', usage: 48, members: 6, region: 'us-east-2' },
  { name: 'workspace-health', plan: 'Enterprise', usage: 55, members: 10, region: 'us-west-2' },
  { name: 'workspace-labs', plan: 'Pro', usage: 21, members: 5, region: 'local' },
]

function DashboardWorkspaces() {
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Workspaces" title="Multi-workspace governance boundaries and usage" description="Track plans, regional deployment, members, and quota consumption across each governed environment." action={<Button>Create Workspace</Button>} />
      <div className="grid gap-5 xl:grid-cols-2">
        {workspaces.map((workspace) => (
          <Card key={workspace.name} variant="interactive">
            <CardHeader>
              <div>
                <div className="text-2xl font-semibold tracking-[-0.04em] text-white">{workspace.name}</div>
                <div className="mt-2 text-sm text-nova-text-secondary">{workspace.members} members · region {workspace.region}</div>
              </div>
              <Badge variant={workspace.plan === 'Enterprise' ? 'info' : 'outline'}>{workspace.plan}</Badge>
            </CardHeader>
            <CardContent>
              <ProgressBar value={workspace.usage} label="Monthly usage" tone="accent" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default DashboardWorkspaces

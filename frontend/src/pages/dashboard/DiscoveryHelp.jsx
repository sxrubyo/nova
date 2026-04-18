import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge, Button, Card, CardContent, CardHeader } from '@/components/ui'
import { PageHeader } from '@/components/PageHeader'
import { BookOpen, Boxes, CheckCircle2, Cpu, Lock, MailWarning, Network, ScanSearch, ShieldCheck, TerminalSquare, Workflow } from 'lucide-react'

const detectionMethods = [
  {
    title: 'VS Code extensions',
    icon: TerminalSquare,
    detail: 'Confirms assistants such as GitHub Copilot, Continue.dev, and Cline from installed extension IDs.',
  },
  {
    title: 'Config files and directories',
    icon: Boxes,
    detail: 'Reads concrete host footprints like ~/.config/cursor, ~/.continue, ~/.aider.conf.yml, and n8n state.',
  },
  {
    title: 'Processes and health probes',
    icon: Cpu,
    detail: 'Verifies live runtimes with process signatures, ports, and lightweight HTTP health checks where available.',
  },
  {
    title: 'Docker and package managers',
    icon: Workflow,
    detail: 'Checks containers, pip packages, npm packages, and binaries when those signals are explicit and reproducible.',
  },
]

const supportedAgents = [
  { name: 'GitHub Copilot', type: 'Code assistant', logo: '/agent-logos/generic.svg' },
  { name: 'Cursor', type: 'AI IDE', logo: '/agent-logos/generic.svg' },
  { name: 'Continue.dev', type: 'Code assistant', logo: '/agent-logos/generic.svg' },
  { name: 'Cline', type: 'Code assistant', logo: '/agent-logos/generic.svg' },
  { name: 'Aider', type: 'Terminal pair programmer', logo: '/agent-logos/generic.svg' },
  { name: 'Codex CLI', type: 'CLI assistant', logo: '/agent-logos/codex.svg' },
  { name: 'OpenClaw', type: 'Interpreter runtime', logo: '/agent-logos/openclaw.svg' },
  { name: 'LangChain', type: 'Agent framework', logo: '/agent-logos/langchain.svg' },
  { name: 'Ollama', type: 'Local LLM', logo: '/agent-logos/generic.svg' },
  { name: 'LM Studio', type: 'Local LLM', logo: '/agent-logos/generic.svg' },
  { name: 'Jan', type: 'Local LLM', logo: '/agent-logos/generic.svg' },
  { name: 'n8n', type: 'Workflow automation', logo: '/agent-logos/n8n.svg' },
]

const connectionSteps = [
  'Install or start the runtime on the same host where Nova runs.',
  'Open Discovery and launch a fresh scan.',
  'Review the evidence count, confidence, and matched signals.',
  'Connect only the runtimes you want Nova to govern.',
]

const privacyPromises = [
  'Discovery runs locally on the host.',
  'Weak signals are filtered out instead of guessed into existence.',
  'Nova reads runtime metadata, not your source code.',
  'The operator decides which detected runtimes become governed agents.',
]

function SupportedAgentCard({ agent }) {
  const [failed, setFailed] = useState(false)
  const showLogo = Boolean(agent.logo) && !failed

  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04]">
          {showLogo ? (
            <img
              src={agent.logo}
              alt={`${agent.name} logo`}
              className="h-7 w-7 object-contain"
              onError={() => setFailed(true)}
            />
          ) : (
            <Cpu className="h-5 w-5 text-nova-accent" />
          )}
        </div>
        <div>
          <div className="text-sm font-semibold text-white">{agent.name}</div>
          <div className="mt-1 text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">{agent.type}</div>
        </div>
      </div>
    </div>
  )
}

function AntiDuplicateRunbook() {
  return (
    <Card variant="glass">
      <CardHeader>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Reference workflow</div>
          <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">n8n + Gmail without duplicate sends</div>
        </div>
        <Badge variant="warning" dot>Production pattern</Badge>
      </CardHeader>
      <CardContent className="grid gap-3">
        {[
          'Trigger or webhook starts the campaign.',
          'Nova OS -> Gmail -> Check Duplicate Email validates recipient + subject against Nova ledger history.',
          'If duplicate is false, Gmail sends the message.',
          'Nova OS -> Governance -> Evaluate Action records the allowed send with its ledger proof.',
          'If you need comparison against historical mail already sitting in Gmail Sent, add Gmail mailbox sync explicitly. That is separate from the current ledger-backed duplicate check.',
        ].map((step, index) => (
          <div key={step} className="flex items-start gap-3 rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3">
            <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-nova-accent/18 text-xs font-semibold text-white">
              {index + 1}
            </div>
            <div className="text-sm leading-6 text-nova-text-secondary">{step}</div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export default function DiscoveryHelp() {
  const navigate = useNavigate()
  const supportedSummary = useMemo(() => `${supportedAgents.length} runtime profiles are currently documented for operators.`, [])

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Discovery Help"
        title="How Nova proves a runtime is real before it enters the control plane"
        description="Discovery is intentionally conservative. A runtime appears only when Nova can confirm enough evidence from the host instead of extrapolating from weak hints."
        action={
          <div className="flex items-center gap-3">
            <Badge variant="outline">{supportedSummary}</Badge>
            <Button onClick={() => navigate('/dashboard/discover')}>
              <ScanSearch className="h-4 w-4" />
              Open discovery
            </Button>
          </div>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <Card variant="glass">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Detection model</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Multi-signal verification only</div>
            </div>
            <Badge variant="success" dot>Strict</Badge>
          </CardHeader>
          <CardContent className="space-y-3">
            {detectionMethods.map((item) => (
              <div key={item.title} className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
                    <item.icon className="h-4.5 w-4.5 text-nova-accent" />
                  </div>
                  <div className="text-sm font-semibold text-white">{item.title}</div>
                </div>
                <p className="mt-3 text-sm leading-6 text-nova-text-secondary">{item.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card variant="glass">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Operator flow</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Connect only what you can defend</div>
            </div>
            <Badge variant="info" dot>Read-only scan</Badge>
          </CardHeader>
          <CardContent className="space-y-3">
            {connectionSteps.map((step, index) => (
              <div key={step} className="flex items-start gap-3 rounded-[22px] border border-white/10 bg-white/[0.03] px-4 py-3">
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-white">
                  {index + 1}
                </div>
                <div className="text-sm leading-6 text-nova-text-secondary">{step}</div>
              </div>
            ))}
            <div className="rounded-[22px] border border-nova-warning/20 bg-nova-warning/8 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <MailWarning className="h-4 w-4 text-nova-warning" />
                Anti-duplicate email protection
              </div>
              <p className="mt-2 text-sm leading-6 text-nova-text-secondary">
                For outbound email workflows, run Nova duplicate checks before Gmail sends and then evaluate the action after send approval so the ledger stays authoritative. Today this protects against duplicates already recorded by Nova, not every message that may already exist in Gmail outside Nova.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card variant="glass">
        <CardHeader>
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Supported runtimes</div>
            <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Profiles Nova can verify today</div>
          </div>
          <Badge variant="outline">
            <BookOpen className="h-3.5 w-3.5" />
            Documented
          </Badge>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {supportedAgents.map((agent) => (
            <SupportedAgentCard key={agent.name} agent={agent} />
          ))}
        </CardContent>
      </Card>

      <AntiDuplicateRunbook />

      <div className="grid gap-5 xl:grid-cols-[0.92fr_1.08fr]">
        <Card variant="glass">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Privacy and security</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">Discovery is local and bounded</div>
            </div>
            <Badge variant="success" dot>
              <ShieldCheck className="h-3.5 w-3.5" />
              Operator-controlled
            </Badge>
          </CardHeader>
          <CardContent className="space-y-3">
            {privacyPromises.map((promise) => (
              <div key={promise} className="flex items-start gap-3 rounded-[20px] border border-white/10 bg-white/[0.03] px-4 py-3">
                <CheckCircle2 className="mt-0.5 h-4.5 w-4.5 shrink-0 text-nova-success" />
                <div className="text-sm leading-6 text-nova-text-secondary">{promise}</div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card variant="glass">
          <CardHeader>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Trust boundaries</div>
              <div className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-white">What Discovery does and does not do</div>
            </div>
            <Badge variant="warning" dot>
              <Lock className="h-3.5 w-3.5" />
              Minimal surface
            </Badge>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <div className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <Network className="h-4 w-4 text-nova-accent" />
                Discovery does
              </div>
              <p className="mt-3 text-sm leading-6 text-nova-text-secondary">
                Read host evidence, probe exposed runtime health, compare signals against strict fingerprints, and publish realtime lifecycle events.
              </p>
            </div>
            <div className="rounded-[22px] border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <ShieldCheck className="h-4 w-4 text-nova-warning" />
                Discovery does not
              </div>
              <p className="mt-3 text-sm leading-6 text-nova-text-secondary">
                Ship your code off-host, mutate runtime installs during scanning, or infer products solely from a single open port with no corroborating signal.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

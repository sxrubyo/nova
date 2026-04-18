import { NavLink } from 'react-router-dom'
import { HelpCircle, Menu, PanelLeftClose, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { NovaLogo } from '@/components/brand/NovaLogo'
import { Badge } from '@/components/ui/core'
import { ProgressBar, Avatar, StatusDot } from '@/components/ui/data-display'
import { cn, formatCompactNumber } from '@/lib/utils'

export function AppSidebar({
  items,
  collapsed,
  onToggle,
  workspace,
  user,
  connectedAgents = [],
}) {
  return (
    <aside
      className={cn(
        'sticky top-0 hidden h-screen flex-col border-r border-white/8 bg-[#090a0f]/94 backdrop-blur-xl lg:flex',
        collapsed ? 'w-[86px]' : 'w-[280px]',
      )}
    >
      <div className="flex items-center justify-between gap-3 px-4 py-5">
        <NovaLogo variant={collapsed ? 'icon' : 'full'} className={collapsed ? 'justify-center' : ''} />
        <button onClick={onToggle} className="rounded-full border border-nova-border p-2 text-nova-text-secondary transition hover:text-white" aria-label="Toggle sidebar">
          {collapsed ? <Menu className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <div className="px-4">
        <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
          <Badge variant="info">Nova OS v4.0.0</Badge>
          {!collapsed && (
            <>
              <p className="mt-4 text-sm leading-6 text-nova-text-secondary">
                Control plane active. Runtime policies, audit chain, and gateway routing are in watch mode.
              </p>
              <div className="mt-4 flex items-center gap-3 rounded-2xl border border-nova-border bg-black/20 px-3 py-2">
                <Sparkles className="h-4 w-4 text-nova-accent-2" />
                <div className="text-xs text-nova-text-secondary">Enterprise governance surface</div>
              </div>
            </>
          )}
        </div>
      </div>

      <nav className="mt-5 flex-1 space-y-1 px-3">
        {items.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            end={item.href === '/dashboard'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-2xl px-3 py-3 text-sm transition',
                isActive
                  ? 'bg-white text-[#090a0f] shadow-glow'
                  : 'text-nova-text-secondary hover:bg-white/[0.05] hover:text-white',
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {connectedAgents.length > 0 && !collapsed && (
        <div className="px-4">
          <div className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Connected</div>
            <div className="mt-3 space-y-2">
              {connectedAgents.slice(0, 6).map((agent) => (
                <NavLink
                  key={agent.id}
                  to={`/dashboard/agents/${agent.id}`}
                  className="flex items-center justify-between rounded-2xl px-3 py-2 text-sm text-nova-text-secondary transition hover:bg-white/[0.05] hover:text-white"
                >
                  <div className="flex items-center gap-3">
                    <StatusDot tone={agent.online ? 'success' : 'gray'} pulse={agent.online} />
                    <span>{agent.name}</span>
                  </div>
                  <span className="text-[11px] uppercase tracking-[0.18em]">{agent.kind}</span>
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4 border-t border-white/8 px-4 py-5">
        <div className="rounded-[24px] border border-nova-border bg-white/[0.03] p-4">
          {!collapsed ? (
            <>
              <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">
                <span>{workspace?.plan || 'Enterprise'}</span>
                <span>{formatCompactNumber(workspace?.usage_this_month || 12847)}</span>
              </div>
              <div className="mt-3">
                <ProgressBar value={((workspace?.usage_this_month || 12847) / Math.max(workspace?.quota_monthly || 50000, 1)) * 100} tone="accent" />
              </div>
            </>
          ) : (
            <div className="flex justify-center"><Badge variant="outline">Pro</Badge></div>
          )}
        </div>

        <button className="flex w-full items-center gap-3 rounded-2xl border border-nova-border bg-white/[0.03] px-4 py-3 text-sm text-nova-text-secondary transition hover:text-white">
          <HelpCircle className="h-4 w-4" />
          {!collapsed && <span>Help & Docs</span>}
        </button>

        <div className={cn('flex items-center gap-3 rounded-2xl border border-nova-border bg-white/[0.03] px-3 py-3', collapsed && 'justify-center')}>
          <Avatar name={user?.name || 'Operator'} status="success" />
          {!collapsed && (
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-white">{user?.name || 'Operator'}</div>
              <div className="truncate text-xs text-nova-text-secondary">{user?.email || 'operator@nova-os.com'}</div>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}

export function MobileSidebarToggle({ onClick }) {
  return (
    <motion.button
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-nova-text-primary lg:hidden"
      aria-label="Open navigation"
    >
      <Menu className="h-5 w-5" />
    </motion.button>
  )
}

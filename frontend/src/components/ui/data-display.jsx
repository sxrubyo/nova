import { Fragment } from 'react'
import * as AvatarPrimitive from '@radix-ui/react-avatar'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronUp, Inbox } from 'lucide-react'
import { cn, clamp, formatRelativeTime, getDecisionTone, getRiskTone, initials } from '@/lib/utils'
import { Badge, Button } from '@/components/ui/core'

export function Skeleton({ className }) {
  return <div className={cn('animate-shimmer rounded-2xl bg-shimmer', className)} />
}

export function StatusDot({ tone = 'success', pulse = false }) {
  const tones = {
    success: 'bg-nova-success',
    warning: 'bg-nova-warning',
    danger: 'bg-nova-danger',
    info: 'bg-nova-info',
    gray: 'bg-nova-text-muted',
  }

  return <span className={cn('inline-block h-2.5 w-2.5 rounded-full', tones[tone], pulse && 'animate-pulse')} />
}

export function Avatar({ name, src, size = 'md', status }) {
  const sizes = {
    xs: 'h-7 w-7 text-[10px]',
    sm: 'h-9 w-9 text-xs',
    md: 'h-11 w-11 text-sm',
    lg: 'h-14 w-14 text-base',
    xl: 'h-20 w-20 text-xl',
  }

  return (
    <div className="relative inline-flex">
      <AvatarPrimitive.Root className={cn('overflow-hidden rounded-full border border-white/10 bg-white/[0.06]', sizes[size])}>
        <AvatarPrimitive.Image src={src} alt={name} className="h-full w-full object-cover" />
        <AvatarPrimitive.Fallback className="flex h-full w-full items-center justify-center font-semibold text-nova-text-primary">
          {initials(name)}
        </AvatarPrimitive.Fallback>
      </AvatarPrimitive.Root>
      {status && <span className="absolute bottom-0 right-0"><StatusDot tone={status} pulse={status === 'success'} /></span>}
    </div>
  )
}

export function ProgressBar({ value = 0, label, tone = 'accent' }) {
  const tones = {
    accent: 'bg-nova-accent',
    success: 'bg-nova-success',
    warning: 'bg-nova-warning',
    danger: 'bg-nova-danger',
    info: 'bg-nova-info',
  }

  return (
    <div>
      {label && <div className="mb-2 flex items-center justify-between text-xs text-nova-text-secondary"><span>{label}</span><span>{Math.round(value)}%</span></div>}
      <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
        <motion.div className={cn('h-full rounded-full', tones[tone])} initial={{ width: 0 }} animate={{ width: `${clamp(value, 0, 100)}%` }} />
      </div>
    </div>
  )
}

export function RiskGauge({ value = 0, size = 112, strokeWidth = 10 }) {
  const radius = size / 2 - strokeWidth
  const circumference = Math.PI * radius
  const progress = circumference - (clamp(value, 0, 100) / 100) * circumference
  const tone = getRiskTone(value)
  const colors = {
    success: 'var(--nova-success)',
    warning: 'var(--nova-warning)',
    danger: 'var(--nova-danger)',
  }

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size / 2 + strokeWidth} viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}>
        <path
          d={`M ${strokeWidth} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth} ${size / 2}`}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <motion.path
          d={`M ${strokeWidth} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth} ${size / 2}`}
          fill="none"
          stroke={colors[tone]}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: progress }}
          transition={{ type: 'spring', stiffness: 90, damping: 18 }}
        />
      </svg>
      <div className="absolute top-8 flex flex-col items-center">
        <span className="font-display text-2xl font-semibold tracking-[-0.05em] text-white">{Math.round(value)}</span>
        <span className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Risk</span>
      </div>
    </div>
  )
}

export function SparkLine({ points = [], className }) {
  if (!points.length) return null
  const width = 120
  const height = 36
  const max = Math.max(...points)
  const min = Math.min(...points)
  const path = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width
      const y = height - ((point - min) / Math.max(max - min || 1, 1)) * height
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className={cn('h-9 w-28', className)}>
      <motion.path
        d={path}
        fill="none"
        stroke="var(--nova-accent-glow)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.9 }}
      />
    </svg>
  )
}

export function HashChain({ entries = [] }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {entries.map((entry, index) => (
        <div key={entry.id || index} className="flex items-center gap-3">
          <div className="rounded-2xl border border-nova-border bg-white/[0.03] px-3 py-2 text-xs text-nova-text-secondary">
            <div className="font-medium text-white">{entry.label || `Block ${index + 1}`}</div>
            <div className="mt-1 font-mono">{entry.hash?.slice(0, 14)}...</div>
          </div>
          {index < entries.length - 1 && <div className="h-px w-8 bg-gradient-to-r from-nova-accent to-nova-accent-2" />}
        </div>
      ))}
    </div>
  )
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[28px] border border-dashed border-nova-border bg-white/[0.02] px-6 py-14 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/[0.04]">
        <Inbox className="h-7 w-7 text-nova-text-secondary" />
      </div>
      <h3 className="mt-5 text-xl font-semibold tracking-[-0.03em] text-white">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-nova-text-secondary">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function Table({
  columns,
  data,
  emptyTitle = 'No data',
  emptyDescription = 'No records match the current filters.',
  expandedRowId,
  onToggleRow,
  renderExpandedRow,
}) {
  if (!data.length) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  return (
    <div className="overflow-hidden rounded-[28px] border border-nova-border">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] text-left">
          <thead className="bg-white/[0.04]">
            <tr className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">
              {columns.map((column) => (
                <th key={column.key} className="px-5 py-4 font-medium">{column.label}</th>
              ))}
              {renderExpandedRow && <th className="w-12 px-5 py-4" />}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => {
              const isExpanded = expandedRowId === row.id
              return (
                <Fragment key={row.id}>
                  <tr className="border-t border-nova-border/60 text-sm text-nova-text-primary transition hover:bg-white/[0.03]">
                    {columns.map((column) => (
                      <td key={column.key} className="px-5 py-4 align-top">
                        {column.render ? column.render(row) : row[column.key]}
                      </td>
                    ))}
                    {renderExpandedRow && (
                      <td className="px-5 py-4">
                        <Button variant="ghost" size="xs" onClick={() => onToggleRow?.(row.id)} aria-label="Toggle row details">
                          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </Button>
                      </td>
                    )}
                  </tr>
                  {isExpanded && renderExpandedRow && (
                    <tr className="border-t border-nova-border/60 bg-white/[0.02]">
                      <td colSpan={columns.length + 1} className="px-5 py-5">
                        {renderExpandedRow(row)}
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function DecisionBadge({ value }) {
  return <Badge variant={getDecisionTone(value)}>{value}</Badge>
}

export function RelativeTime({ value }) {
  return <span className="text-sm text-nova-text-secondary">{formatRelativeTime(value)}</span>
}

import { formatDistanceToNowStrict, format } from 'date-fns'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatNumber(value) {
  return new Intl.NumberFormat('en-US').format(value ?? 0)
}

export function formatCompactNumber(value) {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value ?? 0)
}

export function formatPercent(value, digits = 1) {
  const normalized = Number.isFinite(Number(value)) ? Number(value) : 0
  return `${normalized.toFixed(digits)}%`
}

export function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value ?? 0)
}

export function formatDuration(value, unit = 'ms') {
  if (value == null) return 'n/a'
  return `${value}${unit}`
}

export function formatDateTime(value) {
  if (!value) return 'Unavailable'
  return format(new Date(value), 'MMM d, yyyy HH:mm')
}

export function formatRelativeTime(value) {
  if (!value) return 'just now'
  return `${formatDistanceToNowStrict(new Date(value), { addSuffix: false })} ago`
}

export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

export function getRiskTone(score) {
  if (score >= 61) return 'danger'
  if (score >= 31) return 'warning'
  return 'success'
}

export function getDecisionTone(decision) {
  switch ((decision || '').toLowerCase()) {
    case 'allow':
    case 'approved':
      return 'success'
    case 'block':
    case 'blocked':
      return 'danger'
    case 'escalate':
    case 'escalated':
      return 'warning'
    default:
      return 'info'
  }
}

export function initials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

export function debounceFrame(callback) {
  let frame = 0
  return (...args) => {
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(() => callback(...args))
  }
}

import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { getNovaIsotipoSrc } from '@/lib/nova-brand-assets'

export function NovaLogo({
  className,
  variant = 'full',
  size = 40,
  animated = false,
  tone = 'light',
}) {
  const src = getNovaIsotipoSrc(tone === 'dark' ? 'dark' : 'light')
  const labelSize = Math.max(18, Math.round(size * 0.48))
  const captionSize = Math.max(10, Math.round(size * 0.22))
  const icon = (
    <motion.img
      src={src}
      alt="Nova isotipo"
      className="h-full w-full object-contain"
      animate={
        animated
          ? {
              scale: [1, 1.035, 1],
              opacity: [1, 0.9, 1],
            }
          : undefined
      }
      transition={
        animated
          ? {
              duration: 3.2,
              ease: 'easeInOut',
              repeat: Number.POSITIVE_INFINITY,
            }
          : undefined
      }
    />
  )

  return (
    <div className={cn('inline-flex items-center gap-3', className)}>
      <div
        className="relative shrink-0"
        style={{ width: size, height: size }}
      >
        {animated && (
          <motion.div
            className="absolute inset-0 rounded-full bg-white/12 blur-2xl"
            animate={{ scale: [0.92, 1.08, 0.96], opacity: [0.22, 0.46, 0.22] }}
            transition={{ duration: 2.8, repeat: Number.POSITIVE_INFINITY, ease: 'easeInOut' }}
          />
        )}
        <div className="relative h-full w-full">{icon}</div>
      </div>
      {variant === 'full' && (
        <div className="leading-none">
          <div
            className="font-display font-semibold tracking-[-0.05em] text-white"
            style={{ fontSize: `${labelSize}px` }}
          >
            Nova OS
          </div>
          <div
            className="mt-1 uppercase tracking-[0.22em] text-nova-text-secondary"
            style={{ fontSize: `${captionSize}px` }}
          >
            Governance Control Plane
          </div>
        </div>
      )}
    </div>
  )
}

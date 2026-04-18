import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as Select from '@radix-ui/react-select'
import * as Switch from '@radix-ui/react-switch'
import * as Tabs from '@radix-ui/react-tabs'
import { AnimatePresence, motion } from 'framer-motion'
import { cva } from 'class-variance-authority'
import { Check, ChevronDown, Eye, EyeOff, LoaderCircle, X } from 'lucide-react'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-semibold transition duration-200 ease-out focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-nova-accent text-white shadow-glow hover:scale-[1.02] hover:bg-nova-accent-glow',
        secondary: 'bg-nova-accent-2/14 text-nova-accent-2 hover:bg-nova-accent-2/20',
        outline: 'border border-nova-border bg-transparent text-nova-text-primary hover:border-nova-border-active hover:bg-white/5',
        ghost: 'bg-transparent text-nova-text-secondary hover:bg-white/5 hover:text-nova-text-primary',
        danger: 'bg-nova-danger/16 text-nova-danger hover:bg-nova-danger/22',
        link: 'bg-transparent px-0 text-nova-text-primary hover:text-white',
      },
      size: {
        xs: 'h-8 px-3 text-xs',
        sm: 'h-10 px-4 text-sm',
        md: 'h-12 px-5 text-sm',
        lg: 'h-14 px-7 text-base',
      },
      fullWidth: {
        true: 'w-full',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
)

export function Button({ className, variant, size, loading, fullWidth, children, ...props }) {
  return (
    <button className={cn(buttonVariants({ variant, size, fullWidth }), className)} {...props}>
      {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  )
}

const cardVariants = cva('rounded-[28px] border p-6 transition duration-200 ease-out', {
  variants: {
    variant: {
      default: 'border-nova-border bg-nova-surface',
      elevated: 'border-nova-border bg-nova-surface shadow-panel',
      interactive:
        'border-nova-border bg-nova-surface hover:-translate-y-0.5 hover:border-nova-border-active hover:shadow-glow',
      glass: 'border-white/10 bg-white/[0.04] backdrop-blur-xl',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

export function Card({ className, variant, children }) {
  return <div className={cn(cardVariants({ variant }), className)}>{children}</div>
}

export function CardHeader({ className, children }) {
  return <div className={cn('mb-5 flex items-start justify-between gap-4', className)}>{children}</div>
}

export function CardContent({ className, children }) {
  return <div className={cn('', className)}>{children}</div>
}

export function CardFooter({ className, children }) {
  return <div className={cn('mt-5 flex items-center justify-between gap-3', className)}>{children}</div>
}

const badgeVariants = cva(
  'inline-flex items-center gap-2 rounded-full border px-3 py-1 font-medium uppercase tracking-[0.18em]',
  {
    variants: {
      variant: {
        default: 'border-nova-border bg-white/5 text-nova-text-secondary',
        success: 'border-nova-success/20 bg-nova-success/12 text-nova-success',
        warning: 'border-nova-warning/20 bg-nova-warning/12 text-nova-warning',
        danger: 'border-nova-danger/20 bg-nova-danger/12 text-nova-danger',
        info: 'border-nova-info/20 bg-nova-info/12 text-nova-info',
        outline: 'border-nova-border bg-transparent text-nova-text-primary',
      },
      size: {
        sm: 'text-[10px]',
        md: 'text-[11px]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  },
)

export function Badge({ className, variant, size, dot = false, children }) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}

export function Input({
  label,
  helper,
  error,
  success,
  icon: Icon,
  variant = 'default',
  type = 'text',
  className,
  ...props
}) {
  const [revealed, setRevealed] = useState(false)
  const isPassword = variant === 'password' || type === 'password'
  const actualType = isPassword && !revealed ? 'password' : 'text'

  return (
    <label className="block">
      {label && <span className="mb-2 block text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">{label}</span>}
      <div
        className={cn(
          'relative flex items-center rounded-[18px] border bg-white/[0.04] transition',
          error && 'border-nova-danger/40',
          success && 'border-nova-success/40',
          !error && !success && 'border-nova-border focus-within:border-nova-border-active',
        )}
      >
        {Icon && <Icon className="pointer-events-none absolute left-4 h-4 w-4 text-nova-text-muted" />}
        <input
          type={isPassword ? actualType : type}
          className={cn(
            'w-full rounded-[18px] bg-transparent px-4 py-3.5 text-sm text-nova-text-primary outline-none placeholder:text-nova-text-muted',
            Icon && 'pl-11',
            isPassword && 'pr-11',
            className,
          )}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((value) => !value)}
            className="absolute right-4 text-nova-text-muted transition hover:text-nova-text-primary"
            aria-label={revealed ? 'Hide password' : 'Show password'}
          >
            {revealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
      </div>
      {(helper || error || success) && (
        <span className={cn('mt-2 block text-xs', error ? 'text-nova-danger' : success ? 'text-nova-success' : 'text-nova-text-secondary')}>
          {error || success || helper}
        </span>
      )}
    </label>
  )
}

export function Modal({ open, onOpenChange, title, description, size = 'md', headerAlign = 'left', children }) {
  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
    full: 'max-w-[min(1200px,92vw)]',
  }
  const isCenteredHeader = headerAlign === 'center'

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-50 bg-[#04050a]/70 backdrop-blur-xl"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
                <motion.div
                  initial={{ opacity: 0, scale: 0.96, y: 16 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96, y: 16 }}
                  transition={{ duration: 0.2 }}
                  className={cn(
                    'w-[92vw] rounded-[32px] border border-white/10 bg-nova-surface-2 p-6 shadow-float',
                    sizes[size],
                  )}
                >
                  <div className={cn(isCenteredHeader ? 'relative flex w-full justify-center px-12 text-center' : 'flex items-start justify-between gap-4')}>
                    <div className={cn(isCenteredHeader ? 'mx-auto flex w-full max-w-2xl flex-col items-center text-center' : 'min-w-0 flex-1')}>
                      <Dialog.Title className={cn('text-2xl font-semibold tracking-[-0.04em] text-white', isCenteredHeader && 'w-full text-center')}>
                        {title}
                      </Dialog.Title>
                      {description && (
                        <Dialog.Description
                          className={cn('mt-2 text-sm leading-6 text-nova-text-secondary', isCenteredHeader && 'mx-auto w-full max-w-2xl text-center')}
                        >
                          {description}
                        </Dialog.Description>
                      )}
                    </div>
                    <Dialog.Close asChild>
                      <button
                        className={cn(
                          'rounded-full border border-nova-border p-2 text-nova-text-muted transition hover:text-white',
                          isCenteredHeader && 'absolute right-0 top-0',
                        )}
                        aria-label="Close"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </Dialog.Close>
                  </div>
                  <div className="mt-6">{children}</div>
                </motion.div>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}

export function TabsRoot({ className, ...props }) {
  return <Tabs.Root className={className} {...props} />
}

export function TabsList({ className, ...props }) {
  return <Tabs.List className={cn('inline-flex rounded-full border border-nova-border bg-white/[0.03] p-1', className)} {...props} />
}

export function TabsTrigger({ className, ...props }) {
  return (
    <Tabs.Trigger
      className={cn(
        'rounded-full px-4 py-2 text-sm text-nova-text-secondary transition data-[state=active]:bg-white data-[state=active]:text-[#0d1016]',
        className,
      )}
      {...props}
    />
  )
}

export function TabsContent({ className, ...props }) {
  return <Tabs.Content className={cn('mt-5', className)} {...props} />
}

export function SwitchField({ checked, onCheckedChange, label, description }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-[20px] border border-nova-border bg-white/[0.03] px-4 py-3">
      <div>
        <div className="text-sm font-medium text-nova-text-primary">{label}</div>
        {description && <div className="mt-1 text-xs text-nova-text-secondary">{description}</div>}
      </div>
      <Switch.Root
        checked={checked}
        onCheckedChange={onCheckedChange}
        className="relative h-7 w-12 rounded-full border border-nova-border bg-nova-surface-2 transition data-[state=checked]:bg-nova-accent"
      >
        <Switch.Thumb className="block h-5 w-5 translate-x-1 rounded-full bg-white transition data-[state=checked]:translate-x-6" />
      </Switch.Root>
    </div>
  )
}

export function SelectField({ label, value, onValueChange, options = [], placeholder = 'Select value' }) {
  return (
    <label className="block">
      {label && <span className="mb-2 block text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">{label}</span>}
      <Select.Root value={value} onValueChange={onValueChange}>
        <Select.Trigger className="flex h-12 w-full items-center justify-between rounded-[18px] border border-nova-border bg-white/[0.04] px-4 text-sm text-nova-text-primary">
          <Select.Value placeholder={placeholder} />
          <Select.Icon>
            <ChevronDown className="h-4 w-4 text-nova-text-muted" />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content className="z-50 overflow-hidden rounded-[20px] border border-white/10 bg-nova-surface-2 shadow-panel">
            <Select.Viewport className="p-2">
              {options.map((option) => (
                <Select.Item
                  key={option.value}
                  value={option.value}
                  className="flex cursor-pointer items-center justify-between rounded-xl px-3 py-2 text-sm text-nova-text-primary outline-none hover:bg-white/[0.06]"
                >
                  <Select.ItemText>{option.label}</Select.ItemText>
                  <Select.ItemIndicator>
                    <Check className="h-4 w-4 text-nova-accent-2" />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </label>
  )
}

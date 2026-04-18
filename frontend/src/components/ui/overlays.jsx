import * as Dialog from '@radix-ui/react-dialog'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { motion } from 'framer-motion'
import { Search } from 'lucide-react'
import { Toaster } from 'react-hot-toast'
import { cn } from '@/lib/utils'

export function Tooltip({ children, content }) {
  return (
    <TooltipPrimitive.Provider delayDuration={250}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content sideOffset={8} className="z-50 rounded-xl border border-white/10 bg-nova-surface-2 px-3 py-2 text-xs text-nova-text-primary shadow-panel">
            {content}
            <TooltipPrimitive.Arrow className="fill-nova-surface-2" />
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  )
}

export function Dropdown({ trigger, items = [] }) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>{trigger}</DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="z-50 min-w-[220px] rounded-[20px] border border-white/10 bg-nova-surface-2 p-2 shadow-panel">
          {items.map((item) => (
            <DropdownMenu.Item
              key={item.label}
              className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-nova-text-primary outline-none hover:bg-white/[0.06]"
              onSelect={item.onSelect}
            >
              {item.icon}
              {item.label}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}

export function ToastRegion() {
  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        duration: 3600,
        style: {
          background: 'rgba(18, 18, 26, 0.92)',
          color: '#E8E8F0',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '18px',
          boxShadow: '0 24px 80px -40px rgba(0,0,0,0.65)',
        },
      }}
    />
  )
}

export function CommandPalette({ open, onOpenChange, items = [], onSelect }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay asChild>
          <motion.div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
        </Dialog.Overlay>
        <Dialog.Content asChild>
          <motion.div
            initial={{ opacity: 0, y: 18, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 18, scale: 0.97 }}
            transition={{ duration: 0.18 }}
            className="fixed left-1/2 top-[14vh] z-50 w-[min(680px,92vw)] -translate-x-1/2 rounded-[28px] border border-white/10 bg-nova-surface-2 shadow-float"
          >
            <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
              <Search className="h-5 w-5 text-nova-text-secondary" />
              <div className="text-sm text-nova-text-secondary">Search pages, actions, or recent items</div>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-3">
              {items.map((item) => (
                <button
                  key={`${item.group}-${item.label}`}
                  type="button"
                  onClick={() => {
                    onSelect?.(item)
                    onOpenChange(false)
                  }}
                  className={cn(
                    'flex w-full items-start justify-between rounded-2xl px-4 py-3 text-left transition hover:bg-white/[0.05]',
                    item.group && 'mb-1',
                  )}
                >
                  <div>
                    <div className="text-sm font-medium text-white">{item.label}</div>
                    {item.description && <div className="mt-1 text-xs text-nova-text-secondary">{item.description}</div>}
                  </div>
                  {item.group && <span className="text-[11px] uppercase tracking-[0.18em] text-nova-text-muted">{item.group}</span>}
                </button>
              ))}
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

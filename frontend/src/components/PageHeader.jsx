import { Badge } from '@/components/ui'

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-3xl">
        {eyebrow && <Badge variant="outline">{eyebrow}</Badge>}
        <h1 className="mt-5 font-display text-4xl font-semibold tracking-[-0.06em] text-white">{title}</h1>
        {description && <p className="mt-3 text-base leading-8 text-nova-text-secondary">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

import { cn } from '@/lib/utils'

function ProviderMark({ src, alt, frameClassName, imageClassName }) {
  return (
    <div
      className={cn(
        'flex h-12 w-12 shrink-0 items-center justify-center rounded-[16px] border border-black/8 bg-white/96 p-2.5 shadow-[0_18px_40px_-30px_rgba(0,0,0,0.22)] dark:border-white/[0.08] dark:bg-white/[0.04]',
        frameClassName,
      )}
    >
      <img src={src} alt={alt} className={cn('max-h-6 max-w-6 object-contain', imageClassName)} />
    </div>
  )
}

export default ProviderMark

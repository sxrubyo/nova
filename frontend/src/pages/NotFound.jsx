import { Link } from 'react-router-dom'
import { ArrowLeft, Rocket } from 'lucide-react'
import { NovaLogo } from '@/components/brand/NovaLogo'
import { Button } from '@/components/ui'

function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#05060a] px-4">
      <div className="max-w-2xl rounded-[36px] border border-white/10 bg-white/[0.03] p-10 text-center shadow-float">
        <div className="flex justify-center"><NovaLogo variant="icon" /></div>
        <div className="mt-8 inline-flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/[0.04]">
          <Rocket className="h-7 w-7 text-nova-accent-2" />
        </div>
        <h1 className="mt-6 font-display text-5xl font-semibold tracking-[-0.06em] text-white">This route wasn't in the evaluation plan</h1>
        <p className="mt-4 text-base leading-8 text-nova-text-secondary">
          The requested surface drifted outside the governed map. Return to the control plane and continue from a known state.
        </p>
        <div className="mt-8 flex justify-center">
          <Link to="/"><Button><ArrowLeft className="h-4 w-4" /> Return Home</Button></Link>
        </div>
      </div>
    </div>
  )
}

export default NotFound

import { useEffect, useState } from 'react'
import { Copy, ArrowLeft } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { Link } from 'react-router-dom'
import { NovaLogo } from '@/components/brand/NovaLogo'
import { Button, Card, CardContent, Badge } from '@/components/ui'
import { docsSections } from '@/lib/mock-data'

function Docs() {
  const [active, setActive] = useState(docsSections[0].slug)

  useEffect(() => {
    document.title = 'Documentation | Nova OS'
  }, [])

  return (
    <div className="min-h-screen bg-[#06070b] px-4 py-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-[1440px]">
        <div className="flex items-center justify-between gap-4 rounded-[28px] border border-white/10 bg-white/[0.03] px-6 py-4">
          <NovaLogo />
          <div className="flex items-center gap-3">
            <Link to="/"><Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4" /> Site</Button></Link>
            <Link to="/login"><Button variant="outline" size="sm">Login</Button></Link>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[280px_1fr]">
          <aside className="rounded-[28px] border border-white/10 bg-white/[0.03] p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">Documentation</div>
            <div className="mt-4 space-y-2">
              {docsSections.map((section) => (
                <button
                  key={section.slug}
                  type="button"
                  onClick={() => setActive(section.slug)}
                  className={`w-full rounded-2xl px-4 py-3 text-left text-sm transition ${active === section.slug ? 'bg-white text-[#090a0f]' : 'text-nova-text-secondary hover:bg-white/[0.05] hover:text-white'}`}
                >
                  {section.title}
                </button>
              ))}
            </div>
          </aside>

          <section className="space-y-6">
            {docsSections.map((section) => (
              <Card key={section.slug} variant={active === section.slug ? 'interactive' : 'default'} className={active !== section.slug ? 'opacity-75' : ''}>
                <CardContent>
                  <Badge variant="outline">{section.title}</Badge>
                  <h1 className="mt-5 font-display text-4xl font-semibold tracking-[-0.05em] text-white">{section.title}</h1>
                  <p className="mt-4 max-w-3xl text-base leading-8 text-nova-text-secondary">{section.body}</p>
                  <div className="mt-6 overflow-hidden rounded-[24px] border border-white/10 bg-[#090b10]">
                    <div className="flex items-center justify-between border-b border-white/10 px-4 py-3 text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">
                      <span>Reference</span>
                      <button
                        type="button"
                        onClick={async () => {
                          await navigator.clipboard.writeText(section.code)
                          toast.success('Copied to clipboard')
                        }}
                        className="inline-flex items-center gap-2"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copy
                      </button>
                    </div>
                    <pre className="overflow-x-auto px-4 py-4 text-sm text-nova-text-primary"><code>{section.code}</code></pre>
                  </div>
                </CardContent>
              </Card>
            ))}
          </section>
        </div>
      </div>
    </div>
  )
}

export default Docs

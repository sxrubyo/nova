import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, BriefcaseBusiness } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { NovaLogo } from '@/components/brand/NovaLogo'
import { Button, Input, Badge } from '@/components/ui'
import { useAuth } from '@/hooks/useAuth'
import { validateEmail, validatePassword, validateRequired } from '@/lib/validators'

function Register() {
  const navigate = useNavigate()
  const auth = useAuth()
  const [form, setForm] = useState({
    name: '',
    email: '',
    company: '',
    password: '',
  })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    document.title = 'Request Access | Nova OS'
  }, [])

  const validate = () => {
    const nextErrors = {
      name: validateRequired(form.name, 'Name'),
      email: validateEmail(form.email),
      company: validateRequired(form.company, 'Company'),
      password: validatePassword(form.password),
    }
    setErrors(nextErrors)
    return !Object.values(nextErrors).some(Boolean)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!validate()) return
    setSubmitting(true)
    try {
      await auth.requestAccess(form)
      toast.success(auth.setupStatus.needs_setup ? 'Provisioning details saved' : 'Access request captured')
      navigate('/login')
    } catch (error) {
      toast.error(error.message || 'Unable to submit request')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#05060a] px-4 py-6 lg:px-8 lg:py-8">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-[1440px] overflow-hidden rounded-[40px] border border-white/10 bg-[#0b0d13] shadow-float lg:grid-cols-[0.92fr_1.08fr]">
        <section className="relative hidden overflow-hidden border-r border-white/10 lg:block">
          <div className="absolute inset-0 bg-hero-noise" />
          <div className="absolute inset-0 nova-grid-bg opacity-80" />
          <div className="relative z-10 p-12">
            <NovaLogo />
            <Badge variant="outline" className="mt-12">Request Access</Badge>
            <h1 className="mt-6 max-w-xl font-display text-5xl font-semibold leading-[0.94] tracking-[-0.06em] text-white">
              Bring governance to the front of every autonomous workflow.
            </h1>
            <p className="mt-6 max-w-lg text-base leading-8 text-nova-text-secondary">
              Register your team, define the environment, and stand up the governance layer that operators trust when stakes rise.
            </p>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-12 lg:px-14">
          <div className="w-full max-w-[520px]">
            <Link to="/login" className="inline-flex items-center gap-2 text-sm text-nova-text-secondary transition hover:text-white">
              <ArrowLeft className="h-4 w-4" />
              Back to login
            </Link>
            <div className="mt-8">
              <div className="text-[11px] uppercase tracking-[0.18em] text-nova-text-secondary">
                {auth.setupStatus.needs_setup ? 'Bootstrap environment' : 'Workspace request'}
              </div>
              <h2 className="mt-4 font-display text-4xl font-semibold tracking-[-0.05em] text-white">
                {auth.setupStatus.needs_setup ? 'Prepare the first Nova workspace' : 'Request operator access'}
              </h2>
              <p className="mt-3 text-sm leading-7 text-nova-text-secondary">
                {auth.setupStatus.needs_setup
                  ? 'This environment has not been initialized yet. Capture the operator and organization details to continue.'
                  : 'Submit the team information Nova needs to provision a governed workspace for your operators.'}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="mt-8 space-y-5 rounded-[30px] border border-white/10 bg-white/[0.03] p-6">
              <Input label="Operator name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} error={errors.name} placeholder="Ava Salazar" />
              <Input label="Work email" type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} error={errors.email} placeholder="ava@company.com" />
              <Input label="Company" icon={BriefcaseBusiness} value={form.company} onChange={(event) => setForm((current) => ({ ...current, company: event.target.value }))} error={errors.company} placeholder="Northline Systems" />
              <Input label="Password" variant="password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} error={errors.password} placeholder="Create a strong password" />

              <Button fullWidth size="lg" loading={submitting}>
                {auth.setupStatus.needs_setup ? 'Capture bootstrap details' : 'Submit access request'}
              </Button>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}

export default Register

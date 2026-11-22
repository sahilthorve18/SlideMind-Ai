import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Presentation,
  ShieldCheck,
  Layers,
  ArrowRight,
  Sparkles,
  Zap,
  ArrowLeft,
  Mail,
  BarChart3,
  CheckCircle2,
} from 'lucide-react'
import BrandLogo from '../components/BrandLogo'
import AmbientParticles from '../components/AmbientParticles'
import { useApp } from '../context/AppContext'

export default function Login({ onCancel, onSuccess }) {
  const navigate = useNavigate()
  const { login, guestLogin, toast, startGoogle } = useApp()
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [guestBusy, setGuestBusy] = useState(false)
  const [googleBusy, setGoogleBusy] = useState(false)

  const handleComplete = () => {
    const postLoginRedirect = sessionStorage.getItem('sm_post_login_redirect')
    if (postLoginRedirect) {
      sessionStorage.removeItem('sm_post_login_redirect')
      navigate(postLoginRedirect)
      return
    }
    if (onSuccess) onSuccess()
    else if (onCancel) onCancel()
    else navigate('/')
  }

  const handleBack = () => {
    if (onCancel) onCancel()
    else navigate('/')
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setBusy(true)
    try {
      await login(email.trim())
      toast('Signed in successfully! Welcome to SlideMind AI.', 'success')
      handleComplete()
    } catch (err) {
      toast(err.message || 'Failed to sign in. Please try again.', 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleGuestLogin = async () => {
    setGuestBusy(true)
    try {
      await guestLogin()
      toast('Welcome! You are exploring SlideMind AI as a guest.', 'success')
      handleComplete()
    } catch (err) {
      toast(err.message || 'Failed to start guest session.', 'error')
    } finally {
      setGuestBusy(false)
    }
  }

  const handleGoogle = async () => {
    if (googleBusy) return
    setGoogleBusy(true)
    try {
      await startGoogle()
    } catch (err) {
      if (err.code === 'google_not_configured' || err.status === 503) {
        toast('Google sign-in is not configured on this server. Please use 1-Click Guest Pass or email.', 'info')
      } else {
        toast(err.message || 'Google sign-in failed.', 'error')
      }
      setGoogleBusy(false)
    }
  }

  return (
    <div className="home-shell relative flex min-h-screen w-screen items-center justify-center overflow-hidden text-zinc-100 p-4 md:p-8 bg-[#101114]">
      {/* Obsidian Orange Ambient Animated Particles with Cursor Repulsion */}
      <AmbientParticles />

      {/* Ambient Lighting Orbs */}
      <div className="pointer-events-none fixed -top-40 right-1/4 h-96 w-96 rounded-full bg-[#F28C28]/10 blur-[130px] z-0" />
      <div className="pointer-events-none fixed -bottom-40 left-1/4 h-96 w-96 rounded-full bg-orange-600/5 blur-[140px] z-0" />

      {/* Top Navigation Back link */}
      <button
        onClick={handleBack}
        className="absolute top-6 left-6 md:top-8 md:left-8 z-20 flex items-center gap-2 text-xs font-medium text-[#C5C0B8] hover:text-[#F4E6D3] transition-colors bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] px-3.5 py-1.5 rounded-full cursor-pointer"
      >
        <ArrowLeft size={14} />
        <span>Back to Studio</span>
      </button>

      <div className="relative z-10 grid w-full max-w-5xl items-center gap-12 lg:grid-cols-12">
        {/* Left Side: Brand & Product Architecture */}
        <div className="hidden lg:col-span-7 lg:block space-y-8 pr-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/[0.05] border border-white/[0.08] text-[#F28C28]">
              <BrandLogo size={20} />
            </div>
            <span className="text-base font-bold tracking-tight text-[#F4E6D3]">SlideMind AI</span>
            <span className="rounded-full bg-[#F28C28]/15 border border-[#F28C28]/30 px-2.5 py-0.5 text-[11px] font-medium text-[#F28C28]">
              Studio
            </span>
          </div>

          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-[#F4E6D3] leading-tight sm:text-5xl">
              Deliberate presentation engineering.
            </h1>
            <p className="mt-4 text-base text-[#C5C0B8] max-w-lg leading-relaxed">
              Create executive slide decks with authentic design systems, deep research grounding, intelligent visual selection, and direct Google Slides synchronization.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3.5 pt-2">
            <div className="liquid-glass-card rounded-xl p-4">
              <div className="flex items-center gap-2 text-[#F28C28] mb-1.5">
                <Layers size={16} />
                <span className="text-xs font-semibold text-[#F4E6D3]">15 Design Systems</span>
              </div>
              <p className="text-xs text-[#888A90] leading-relaxed">
                Swiss International, Keynote, Brutalist, Financial, and Editorial layouts.
              </p>
            </div>

            <div className="liquid-glass-card rounded-xl p-4">
              <div className="flex items-center gap-2 text-[#F28C28] mb-1.5">
                <ShieldCheck size={16} />
                <span className="text-xs font-semibold text-[#F4E6D3]">Verified Grounding</span>
              </div>
              <p className="text-xs text-[#888A90] leading-relaxed">
                Source citations from documents and web search without hallucinated metrics.
              </p>
            </div>

            <div className="liquid-glass-card rounded-xl p-4">
              <div className="flex items-center gap-2 text-[#F28C28] mb-1.5">
                <BarChart3 size={16} />
                <span className="text-xs font-semibold text-[#F4E6D3]">Visual Intelligence</span>
              </div>
              <p className="text-xs text-[#888A90] leading-relaxed">
                Semantic image search, live Commons retrieval, and focal-point aware layouts.
              </p>
            </div>

            <div className="liquid-glass-card rounded-xl p-4">
              <div className="flex items-center gap-2 text-[#F28C28] mb-1.5">
                <Presentation size={16} />
                <span className="text-xs font-semibold text-[#F4E6D3]">Google Slides API</span>
              </div>
              <p className="text-xs text-[#888A90] leading-relaxed">
                Two-way cloud synchronization and PowerPoint/PDF instant downloads.
              </p>
            </div>
          </div>
        </div>

        {/* Right Side: Clean Authentication Card */}
        <div className="w-full lg:col-span-5 max-w-md mx-auto">
          <div className="liquid-glass-modal p-7 sm:p-8 shadow-2xl">
            <div className="text-center mb-6">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.05] border border-white/[0.08] text-[#F28C28] lg:hidden">
                <BrandLogo size={24} />
              </div>
              <h2 className="text-xl font-bold text-[#F4E6D3] tracking-tight">Access SlideMind Studio</h2>
              <p className="mt-1 text-xs text-[#888A90]">
                Choose your preferred way to start creating presentations
              </p>
            </div>

            {/* Option 1: 1-Click Instant Guest Pass (Easiest for friends/reviewers) */}
            <button
              type="button"
              onClick={handleGuestLogin}
              disabled={guestBusy || busy}
              className="liquid-glass-btn-primary w-full flex items-center justify-between rounded-2xl px-4 py-3 text-xs font-semibold active:scale-98 transition disabled:opacity-50 cursor-pointer mb-3 group text-[#101114]"
            >
              <div className="flex items-center gap-2.5">
                <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-[#101114]/20">
                  <Zap size={14} className="text-[#101114]" />
                </div>
                <div className="text-left">
                  <div className="font-semibold text-[#101114]">⚡ 1-Click Guest Pass</div>
                  <div className="text-[10px] text-[#101114]/80 font-normal">Instant demo access · No setup required</div>
                </div>
              </div>
              {guestBusy ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#101114] border-t-transparent" />
              ) : (
                <ArrowRight size={15} className="text-[#101114]/80 group-hover:translate-x-0.5 transition-transform" />
              )}
            </button>

            {/* Option 2: Google OAuth Button */}
            <button
              type="button"
              onClick={handleGoogle}
              disabled={googleBusy}
              className="liquid-glass-btn w-full flex items-center justify-center gap-3 rounded-2xl px-4 py-2.5 text-xs font-medium text-[#F4E6D3] transition active:scale-98 cursor-pointer disabled:opacity-50"
            >
              {googleBusy ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-orange-400 border-t-transparent" />
              ) : (
                <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
              )}
              <span>{googleBusy ? 'Connecting to Google...' : 'Continue with Google'}</span>
            </button>

            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/[0.08]" />
              </div>
              <div className="relative flex justify-center text-[11px]">
                <span className="bg-[#17191E] px-2.5 text-[#888A90]">or with your email</span>
              </div>
            </div>

            {/* Option 3: Passwordless Email Form */}
            <form onSubmit={submit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-[#C5C0B8] mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#888A90]" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="friend@company.com"
                    className="w-full rounded-xl bg-[#1E2026] border border-white/[0.12] pl-9 pr-3.5 py-2.5 text-xs text-[#F4E6D3] placeholder:text-[#888A90] focus:outline-none focus:border-[#F28C28] transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={busy || guestBusy}
                className="liquid-glass-btn w-full text-[#F4E6D3] px-4 py-2.5 text-xs font-semibold active:scale-98 transition disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
              >
                {busy ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#F28C28] border-t-transparent" />
                    <span>Signing in...</span>
                  </div>
                ) : (
                  <>
                    <span>Continue with Email</span>
                    <ArrowRight size={13} className="text-[#888A90]" />
                  </>
                )}
              </button>
            </form>

            <p className="mt-4 text-center text-[10px] text-[#888A90] leading-relaxed">
              By continuing, you agree to our{' '}
              <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-[#F28C28] hover:underline font-medium">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="/privacy" target="_blank" rel="noopener noreferrer" className="text-[#F28C28] hover:underline font-medium">
                Privacy Policy
              </a>.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

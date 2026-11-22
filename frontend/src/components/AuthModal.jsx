import { useState } from 'react'
import { X, Zap, Mail, ArrowRight, ShieldCheck } from 'lucide-react'
import BrandLogo from './BrandLogo'
import { useApp } from '../context/AppContext'

export default function AuthModal({ onClose }) {
  const {
    login,
    guestLogin,
    startGoogle,
    toast,
    authModalConfig,
    closeAuthModal,
  } = useApp()

  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [guestBusy, setGuestBusy] = useState(false)
  const [googleBusy, setGoogleBusy] = useState(false)

  const handleClose = () => {
    if (onClose) onClose()
    else closeAuthModal()
  }

  const handleGuest = async () => {
    if (guestBusy || busy || googleBusy) return
    setGuestBusy(true)
    try {
      const u = await guestLogin()
      toast('Signed in as Guest Explorer. Welcome!', 'success')
      if (authModalConfig?.onSuccess) {
        authModalConfig.onSuccess(u)
      }
      handleClose()
    } catch (err) {
      toast(err.message || 'Failed to start guest session.', 'error')
    } finally {
      setGuestBusy(false)
    }
  }

  const handleGoogle = async () => {
    if (googleBusy || guestBusy || busy) return
    setGoogleBusy(true)
    try {
      if (authModalConfig?.pendingMessage) {
        sessionStorage.setItem('sm_pending_prompt', authModalConfig.pendingMessage)
      }
      sessionStorage.setItem('sm_post_login_redirect', window.location.pathname + window.location.search)
      await startGoogle(window.location.origin)
    } catch (err) {
      if (err.code === 'google_not_configured' || err.status === 503) {
        toast('Google sign-in is not configured on this server. Please use Guest Pass or email.', 'info')
      } else {
        toast(err.message || 'Google sign-in failed.', 'error')
      }
      setGoogleBusy(false)
    }
  }

  const handleEmailSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim() || busy || guestBusy || googleBusy) return
    setBusy(true)
    try {
      const u = await login(email.trim())
      toast('Signed in successfully!', 'success')
      if (authModalConfig?.onSuccess) {
        authModalConfig.onSuccess(u)
      }
      handleClose()
    } catch (err) {
      toast(err.message || 'Failed to sign in. Please try again.', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md animate-in fade-in duration-200"
      onClick={handleClose}
    >
      {/* Premium Obsidian Glow Effect */}
      <div className="pointer-events-none fixed -top-24 right-1/4 h-72 w-72 rounded-full bg-[#F28C28]/15 blur-[120px]" />
      <div className="pointer-events-none fixed -bottom-24 left-1/4 h-72 w-72 rounded-full bg-orange-600/10 blur-[130px]" />

      <div
        className="liquid-glass-modal relative w-full max-w-md p-6 sm:p-7 shadow-2xl rounded-3xl border border-white/[0.14] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={handleClose}
          aria-label="Close"
          className="absolute top-4 right-4 h-8 w-8 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] flex items-center justify-center text-[#888A90] hover:text-[#F4E6D3] transition-colors cursor-pointer"
        >
          <X size={16} />
        </button>

        {/* Header with Brand Icon */}
        <div className="text-center mb-6 pt-1">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-white/[0.06] border border-white/[0.1] text-[#F28C28] shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]">
            <BrandLogo size={22} />
          </div>
          <h2 className="text-lg sm:text-xl font-bold text-[#F4E6D3] tracking-tight">
            {authModalConfig?.message || 'Sign in to continue chatting with SlideMind AI.'}
          </h2>
          <p className="mt-1.5 text-xs text-[#888A90] leading-relaxed">
            Choose your preferred way to continue creating and modifying presentations.
          </p>
        </div>

        {/* Message Preservation Pill */}
        {authModalConfig?.pendingMessage && (
          <div className="mb-4 rounded-xl bg-white/[0.03] border border-white/[0.08] p-3 text-left">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#F28C28] uppercase tracking-wider mb-1">
              <ShieldCheck size={12} />
              <span>Preserved Message</span>
            </div>
            <p className="text-xs text-[#C5C0B8] line-clamp-2 italic">
              "{authModalConfig.pendingMessage}"
            </p>
          </div>
        )}

        {/* Action 1: Continue with Google */}
        <button
          type="button"
          onClick={handleGoogle}
          disabled={googleBusy || guestBusy || busy}
          className="liquid-glass-btn w-full flex items-center justify-center gap-3 rounded-2xl px-4 py-2.5 text-xs font-medium text-[#F4E6D3] transition active:scale-98 cursor-pointer disabled:opacity-50 mb-3"
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

        {/* Action 2: Continue as Guest (Explicit Opt-in) */}
        <button
          type="button"
          onClick={handleGuest}
          disabled={guestBusy || busy || googleBusy}
          className="liquid-glass-btn-primary w-full flex items-center justify-between rounded-2xl px-4 py-2.5 text-xs font-semibold active:scale-98 transition disabled:opacity-50 cursor-pointer mb-3 group text-[#101114]"
        >
          <div className="flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-[#101114]/20">
              <Zap size={14} className="text-[#101114]" />
            </div>
            <div className="text-left">
              <div className="font-semibold text-[#101114]">⚡ Continue as Guest</div>
              <div className="text-[10px] text-[#101114]/80 font-normal">Instant demo access · No setup required</div>
            </div>
          </div>
          {guestBusy ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#101114] border-t-transparent" />
          ) : (
            <ArrowRight size={14} className="text-[#101114]/80 group-hover:translate-x-0.5 transition-transform" />
          )}
        </button>

        {/* Divider */}
        <div className="relative my-3.5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/[0.08]" />
          </div>
          <div className="relative flex justify-center text-[10px]">
            <span className="bg-[#17191E] px-2.5 text-[#888A90]">or with email</span>
          </div>
        </div>

        {/* Action 3: Email Sign In / Create Account */}
        <form onSubmit={handleEmailSubmit} className="space-y-2.5">
          <div className="relative">
            <Mail size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#888A90]" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full rounded-xl bg-[#1E2026] border border-white/[0.12] pl-9 pr-3.5 py-2 text-xs text-[#F4E6D3] placeholder:text-[#888A90] focus:outline-none focus:border-[#F28C28] transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={busy || guestBusy || googleBusy}
            className="liquid-glass-btn w-full text-[#F4E6D3] px-4 py-2 text-xs font-semibold active:scale-98 transition disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
          >
            {busy ? (
              <div className="flex items-center justify-center gap-2">
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#F28C28] border-t-transparent" />
                <span>Signing in...</span>
              </div>
            ) : (
              <>
                <span>Sign In / Create Account</span>
                <ArrowRight size={13} className="text-[#888A90]" />
              </>
            )}
          </button>
        </form>

        {/* Action 4: Cancel / Close */}
        <div className="mt-4 pt-3 border-t border-white/[0.06] text-center">
          <button
            type="button"
            onClick={handleClose}
            className="text-xs text-[#888A90] hover:text-[#F4E6D3] transition-colors cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

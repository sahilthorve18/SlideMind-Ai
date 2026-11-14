import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../services/api'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

export function AppProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem('sm_theme') || 'dark')
  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)
  const [activeJobId, setActiveJobIdState] = useState(() => {
    try {
      return localStorage.getItem('sm_active_job_id') || null
    } catch {
      return null
    }
  })
  const [activePresentationId, setActivePresentationIdState] = useState(() => {
    try {
      return localStorage.getItem('sm_active_pres_id') || null
    } catch {
      return null
    }
  })
  const [presentationsVersion, setPresentationsVersion] = useState(0)
  const [isPresenting, setIsPresenting] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  const setActiveJobId = useCallback((id) => {
    setActiveJobIdState(id)
    try {
      if (id) localStorage.setItem('sm_active_job_id', id)
      else localStorage.removeItem('sm_active_job_id')
    } catch {}
  }, [])

  const setActivePresentationId = useCallback((id) => {
    setActivePresentationIdState(id)
    try {
      if (id) localStorage.setItem('sm_active_pres_id', id)
      else localStorage.removeItem('sm_active_pres_id')
    } catch {}
  }, [])

  const notifyPresentationsUpdated = useCallback(() => {
    setPresentationsVersion((v) => v + 1)
  }, [])

  const [toasts, setToasts] = useState([])
  const [preferences, setPreferences] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('sm_preferences')) || {
        defaultDesignSystem: 'futuristic_ai',
        defaultSlideCount: 10,
        defaultFormat: 'pptx',
        density: 'balanced',
        autoAudit: true,
      }
    } catch {
      return {
        defaultDesignSystem: 'futuristic_ai',
        defaultSlideCount: 10,
        defaultFormat: 'pptx',
        density: 'balanced',
        autoAudit: true,
      }
    }
  })

  const updatePreferences = (newPrefs) => {
    setPreferences((prev) => {
      const updated = { ...prev, ...newPrefs }
      localStorage.setItem('sm_preferences', JSON.stringify(updated))
      return updated
    })
  }

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('sm_theme', theme)
  }, [theme])

  const ERRORS = {
    google_denied: 'Google access was not granted.', invalid_state: 'Sign-in expired or was tampered with. Please try again.',
    google_failed: 'Google sign-in failed. Please try again.', email_unverified: 'Your Google email is not verified.',
    google_not_configured: 'Google sign-in is not configured on this server.',
  }

  // Finish a Google redirect: the backend puts our session token + the state in the URL fragment.
  const finishGoogleRedirect = () => {
    const hash = window.location.hash.replace(/^#/, '')
    const params = new URLSearchParams(hash)
    if (!params.has('token') && !params.has('error')) return null
    window.history.replaceState(null, '', window.location.pathname + window.location.search) // scrub token from the URL
    if (params.get('error')) return { error: ERRORS[params.get('error')] || 'Sign-in failed.' }
    const expected = sessionStorage.getItem('sm_oauth_state') || localStorage.getItem('sm_oauth_state')
    sessionStorage.removeItem('sm_oauth_state')
    localStorage.removeItem('sm_oauth_state')
    if (expected && params.get('state') && expected !== params.get('state')) {
      return { error: ERRORS.invalid_state } // not started in this browser or state mismatch
    }
    const token = params.get('token')
    if (token) {
      localStorage.setItem('sm_token', token)
      return { ok: true }
    }
    return null
  }

  useEffect(() => {
    const redirect = finishGoogleRedirect()
    if (redirect?.error) toast(redirect.error, 'error')
    const token = localStorage.getItem('sm_token')
    if (!token) {
      api.guestLogin()
        .then((res) => {
          localStorage.setItem('sm_token', res.token)
          setUser(res.user)
        })
        .catch(() => {})
        .finally(() => setAuthReady(true))
      return
    }
    api.me()
      .then((u) => {
        setUser(u)
        if (redirect?.ok) toast('Signed in with Google.', 'success')
      })
      .catch(() => {
        localStorage.removeItem('sm_token')
        api.guestLogin()
          .then((res) => {
            localStorage.setItem('sm_token', res.token)
            setUser(res.user)
          })
          .catch(() => {})
      })
      .finally(() => setAuthReady(true))
  }, [])

  const startGoogle = async () => {
    const { auth_url, state } = await api.googleStart()
    sessionStorage.setItem('sm_oauth_state', state)
    localStorage.setItem('sm_oauth_state', state)
    window.location.assign(auth_url)
  }
  const disconnectGoogle = async () => setUser(await api.googleDisconnect())

  const toast = useCallback((message, type = 'info') => {
    const id = crypto.randomUUID()
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500)
  }, [])

  const login = async (email) => {
    let res
    try {
      res = await api.devLogin(email)
    } catch (err) {
      res = await api.emailLogin(email)
    }
    localStorage.setItem('sm_token', res.token)
    setUser(res.user)
    return res.user
  }

  const guestLogin = async () => {
    const res = await api.guestLogin()
    localStorage.setItem('sm_token', res.token)
    setUser(res.user)
    return res.user
  }

  const logout = () => {
    localStorage.removeItem('sm_token')
    sessionStorage.removeItem('sm_oauth_state')
    localStorage.removeItem('sm_oauth_state')
    document.cookie = 'sm_token=; Max-Age=0; path=/;'
    setUser(null)
  }

  return (
    <Ctx.Provider
      value={{
        theme,
        setTheme,
        user,
        authReady,
        login,
        guestLogin,
        logout,
        toast,
        toasts,
        startGoogle,
        disconnectGoogle,
        preferences,
        updatePreferences,
        activeJobId,
        setActiveJobId,
        activePresentationId,
        setActivePresentationId,
        presentationsVersion,
        notifyPresentationsUpdated,
        isPresenting,
        setIsPresenting,
        commandPaletteOpen,
        setCommandPaletteOpen,
      }}
    >
      {children}
    </Ctx.Provider>
  )
}

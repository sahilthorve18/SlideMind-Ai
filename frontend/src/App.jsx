import { Suspense, lazy, useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import FloatingNavigation from './components/FloatingNavigation'
import DocumentsPanel from './components/DocumentsPanel'
import SettingsModal from './components/SettingsModal'
import Toasts from './components/Toasts'
import CommandPalette from './components/CommandPalette'
import AmbientParticles from './components/AmbientParticles'
import Home from './pages/Home'
import Chat from './pages/Chat'
import Templates from './pages/Templates'
const Presentations = lazy(() => import('./pages/Presentations'))
import Login from './pages/Login'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import ErrorBoundary from './components/ErrorBoundary'
import { useApp } from './context/AppContext'
import { api } from './services/api'

function viewFromPath(path) {
  if (path.startsWith('/chat')) return 'chat'
  if (path.startsWith('/templates')) return 'templates'
  if (path.startsWith('/presentations')) return 'presentations'
  return 'home'
}

export default function App() {
  const { user, authReady, toast } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [docsOpen, setDocsOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [editing, setEditing] = useState(null)

  const refreshHistory = useCallback(() => {
    api.history().catch((e) => toast(e.message, 'error'))
  }, [toast])

  useEffect(() => {
    if (user) refreshHistory()
  }, [user, refreshHistory])

  const openDocuments = () => {
    if (!user) setShowLoginModal(true)
    else setDocsOpen(true)
  }

  const handleNavigate = (targetView) => {
    if (targetView === 'home') navigate('/')
    else if (targetView === 'chat') {
      const id = sessionStorage.getItem('sm_active_chat') || localStorage.getItem('sm_active_chat')
      navigate(id ? `/chat/${id}` : '/chat')
    } else if (targetView === 'templates') navigate('/templates')
    else if (targetView === 'presentations') navigate('/presentations')
  }

  if (!authReady) return null

  if (showLoginModal) {
    return (
      <>
        <Login
          onCancel={() => {
            setShowLoginModal(false)
          }}
          onSuccess={() => {
            setShowLoginModal(false)
          }}
        />
        <Toasts />
      </>
    )
  }

  return (
    <>
      <div className="min-h-screen bg-[#101114] text-[#F4E6D3] overflow-x-hidden selection:bg-[#F28C28]/30 selection:text-[#F4E6D3] relative">
        {/* Obsidian Orange Ambient Animated Particles */}
        {location.pathname !== '/login' && <AmbientParticles />}

        <FloatingNavigation
          currentView={viewFromPath(location.pathname)}
          onNavigate={handleNavigate}
          onOpenDocuments={openDocuments}
          onOpenSettings={() => {
            if (!user) setShowLoginModal(true)
            else setSettingsOpen(true)
          }}
          onOpenLogin={() => setShowLoginModal(true)}
        />

        <div className="relative z-10 min-h-screen">
          <Routes>
            <Route
              path="/"
              element={
                <Home
                  onNavigate={handleNavigate}
                  onStartWithPrompt={() => navigate('/chat')}
                  onOpenDocuments={openDocuments}
                  onRequireLogin={() => setShowLoginModal(true)}
                />
              }
            />
            <Route
              path="/login"
              element={
                <Login
                  onCancel={() => navigate('/')}
                  onSuccess={() => navigate('/')}
                />
              }
            />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route
              path="/chat/:conversationId?"
              element={
                <ChatRoute
                  refreshHistory={refreshHistory}
                  editing={editing}
                  onClearPresentation={() => setEditing(null)}
                />
              }
            />
            <Route
              path="/templates"
              element={
                <div className="pt-24 min-h-screen">
                  <Templates
                    onUseTemplate={(tmpl) =>
                      navigate('/presentations/new', {
                        state: { theme: tmpl.id, topic: tmpl.sampleTitle },
                      })
                    }
                    onBack={() => navigate('/')}
                  />
                </div>
              }
            />
            <Route
              path="/presentations/:presentationId?"
              element={
                <div className="pt-24 min-h-screen">
                  <Suspense
                    fallback={
                      <div className="flex h-screen items-center justify-center text-sm text-outline font-mono">
                        Loading presentation engine…
                      </div>
                    }
                  >
                    <Presentations
                      onEditInChat={(pres) => {
                        setEditing(pres)
                        sessionStorage.removeItem('sm_active_chat')
                        navigate('/chat')
                      }}
                    />
                  </Suspense>
                </div>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>

      {docsOpen && <DocumentsPanel onClose={() => setDocsOpen(false)} />}
      {settingsOpen && (
        <SettingsModal
          onClose={() => setSettingsOpen(false)}
          onOpenLogin={() => {
            setSettingsOpen(false)
            setShowLoginModal(true)
          }}
        />
      )}
      <Toasts />
      <CommandPalette />
    </>
  )
}

function ChatRoute({ refreshHistory, editing, onClearPresentation }) {
  const { conversationId } = useParams()
  const navigate = useNavigate()

  const handleConversationChange = useCallback((id) => {
    if (id) {
      sessionStorage.setItem('sm_active_chat', id)
      localStorage.setItem('sm_active_chat', id)
      navigate(`/chat/${id}`, { replace: true })
    } else {
      sessionStorage.removeItem('sm_active_chat')
      localStorage.removeItem('sm_active_chat')
      navigate('/chat', { replace: true })
    }
  }, [navigate])

  return (
    <div className="min-h-screen">
      <ErrorBoundary>
        <Chat
          conversationId={conversationId || null}
          onConversationChange={handleConversationChange}
          onMenu={() => {}}
          refreshHistory={refreshHistory}
          presentation={editing}
          onClearPresentation={onClearPresentation}
          onOpenPresentations={() => navigate('/presentations')}
          onOpenTemplates={() => navigate('/templates')}
        />
      </ErrorBoundary>
    </div>
  )
}

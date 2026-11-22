import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Loader2,
  Plus,
  Presentation as Icon,
  Search,
  Download,
  Calendar,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Layers,
} from 'lucide-react'
import GenerateForm from '../components/GenerateForm'
import JobProgress from '../components/JobProgress'
import Workspace from './Workspace'
import SlideView from '../components/SlideView'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'
import { triggerFileDownload } from '../utils/download'
import { getDesignSystemById } from '../services/designSystems'

/** list -> new (form) -> job (progress) -> workspace -> audience. The URL owns that step. */
export default function Presentations({ onEditInChat }) {
  const { presentationId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const jobFromUrl = searchParams.get('job')
  const viewParam = searchParams.get('view')
  const mode = viewParam === 'audience' ? 'audience' : jobFromUrl ? 'job' : presentationId === 'new' ? 'new' : presentationId ? 'workspace' : 'list'
  const { user, toast, activeJobId, presentationsVersion, openAuthModal } = useApp()
  const [rows, setRows] = useState(null)
  const [search, setSearch] = useState('')
  const selectedTheme = mode === 'new' ? location.state?.theme || null : null
  const selectedTopic = mode === 'new' ? location.state?.topic || null : null

  const refresh = () => {
    if (!user) {
      setRows([])
      return
    }
    api
      .presentations()
      .then(setRows)
      .catch((e) => {
        setRows([])
        toast(e.message, 'error')
      })
  }

  useEffect(() => {
    if (mode === 'list') refresh()
  }, [mode, user, presentationsVersion])

  useEffect(() => {
    if (mode !== 'list' || !activeJobId) return
    const interval = setInterval(refresh, 3000)
    return () => clearInterval(interval)
  }, [mode, activeJobId])

  if (mode === 'audience')
    return (
      <AudienceWindow
        presentationId={presentationId}
        initialSlide={Number(searchParams.get('slide') || 0)}
      />
    )

  if (mode === 'new')
    return (
      <div className="h-full overflow-y-auto">
        <GenerateForm
          initialTheme={selectedTheme}
          initialTopic={selectedTopic}
          onCancel={() => navigate('/presentations')}
          onStarted={(j) => navigate(`/presentations/new?job=${j.job_id}`)}
        />
      </div>
    )

  if (mode === 'job')
    return (
      <div className="h-full overflow-y-auto">
        <JobProgress
          jobId={jobFromUrl}
          onRetry={() => navigate('/presentations/new')}
          onDone={(r) => navigate(`/presentations/${r.presentation_id}`)}
        />
      </div>
    )

  if (mode === 'workspace')
    return (
      <Workspace
        presentationId={presentationId}
        onBack={() => navigate('/presentations')}
        onEditInChat={onEditInChat}
      />
    )

  const filtered = (rows || []).filter((r) =>
    (r.title || '').toLowerCase().includes(search.toLowerCase())
  )

  const handleDownload = async (e, item, format) => {
    e.stopPropagation()
    try {
      toast(`Preparing ${format.toUpperCase()} download...`, 'info')
      let blob
      try {
        blob = await api.downloadPresentation(item.id, format)
      } catch {
        blob = await api.exportPresentation(item.id, format)
      }
      triggerFileDownload(blob, item.title, format)
      toast(`${format.toUpperCase()} download initiated!`, 'success')
    } catch (err) {
      toast(err.message || 'Download failed.', 'error')
    }
  }

  return (
    <div className="home-shell relative min-h-screen overflow-y-auto text-on-surface p-3 sm:p-6 md:p-8 pt-20 sm:pt-28 md:pt-36">
      <div className="mx-auto max-w-5xl">
        {/* Header Hero */}
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[#F4E6D3] md:text-3xl">
              My Presentations
            </h1>
            <p className="mt-1 text-xs text-[#C5C0B8]">
              Manage your AI-generated decks, view slide analytics, and export to PPTX or PDF.
            </p>
          </div>
          <button
            onClick={() => navigate('/presentations/new')}
            className="liquid-glass-btn-primary flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold text-[#101114] cursor-pointer"
          >
            <Plus size={15} />
            <span>New Presentation</span>
          </button>
        </div>

        {/* Active Generation Banner */}
        {activeJobId && (
          <div className="mb-6 rounded-2xl border border-[#F28C28]/35 bg-[#F28C28]/10 p-4 flex items-center justify-between backdrop-blur-xl shadow-lg">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-[#F28C28]/20 border border-[#F28C28]/30 flex items-center justify-center text-[#F28C28]">
                <Sparkles size={16} className="animate-spin" />
              </div>
              <div>
                <p className="text-xs font-medium text-[#F4E6D3]">Presentation generating in background</p>
                <p className="text-[11px] text-[#C5C0B8]">You can monitor live progress in Studio or view finished decks here.</p>
              </div>
            </div>
            <button
              onClick={() => {
                const id = sessionStorage.getItem('sm_active_chat') || localStorage.getItem('sm_active_chat')
                navigate(id ? `/chat/${id}` : '/chat')
              }}
              className="liquid-glass-btn text-xs px-3.5 py-1.5 rounded-full text-[#F4E6D3] font-medium transition-all cursor-pointer"
            >
              Open in Studio
            </button>
          </div>
        )}

        {/* Search Bar */}
        {rows && rows.length > 0 && (
          <div className="mb-6">
            <div className="relative max-w-md">
              <Search
                size={15}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#888A90]"
              />
              <input
                type="text"
                placeholder="Search presentations..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-xl border border-white/[0.14] bg-white/[0.055] py-2 pl-9 pr-4 text-xs text-[#F4E6D3] placeholder:text-[#888A90] outline-none focus:border-[#F28C28]/60 backdrop-blur-md transition-colors"
              />
            </div>
          </div>
        )}

        {/* Loading Spinner */}
        {rows === null && (
          <div className="flex flex-col items-center justify-center py-20 text-[#888A90]">
            <Loader2 className="animate-spin text-[#F28C28]" size={32} />
            <span className="mt-3 text-xs text-[#C5C0B8]">Loading your presentations...</span>
          </div>
        )}

        {/* Empty / Signed-out State */}
        {rows?.length === 0 && (
          <div className="liquid-glass-card p-12 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#F28C28]/15 text-[#F28C28] border border-[#F28C28]/30">
              <Sparkles size={24} />
            </div>
            <h3 className="mt-4 text-base font-bold text-[#F4E6D3]">
              {!user ? 'Sign in to view your presentations' : 'No presentations yet'}
            </h3>
            <p className="mx-auto mt-1 max-w-sm text-xs text-[#C5C0B8]">
              {!user
                ? 'Sign in or continue as guest to create, edit, and manage your architectural presentations.'
                : 'Create your first art-directed presentation using our 10+ design systems, or generate one in chat!'}
            </p>
            <button
              onClick={() => {
                if (!user) openAuthModal?.({ message: 'Sign in to access your presentations.' })
                else navigate('/presentations/new')
              }}
              className="liquid-glass-btn-primary mt-5 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold text-[#101114] cursor-pointer"
            >
              {!user ? <span>Sign In to SlideMind</span> : <><Plus size={14} /> Create New Deck</>}
            </button>
          </div>
        )}

        {/* Presentation Cards Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((r) => (
            <div
              key={r.id}
              onClick={() => navigate(`/presentations/${r.id}`)}
              className="liquid-glass-card group flex cursor-pointer flex-col justify-between p-5 transition-all duration-300 hover:border-[#F28C28]/35"
            >
              <div>
                {/* Top Badge Row */}
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1 rounded-md bg-white/[0.06] border border-white/[0.08] px-2 py-0.5 text-[10px] font-medium text-[#C5C0B8]">
                    <Layers size={11} />
                    <span>{r.slide_count || 10} Slides</span>
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      r.google_url
                        ? 'bg-[#F28C28]/15 text-[#DFA36D] border border-[#F28C28]/30'
                        : 'bg-emerald-500/15 text-emerald-300 border border-emerald-400/20'
                    }`}
                  >
                    {r.google_url ? 'Google Slides' : 'Native Deck'}
                  </span>
                </div>

                {/* Title */}
                <h3 className="mt-3 line-clamp-2 text-sm font-bold text-[#F4E6D3] transition group-hover:text-[#F28C28]">
                  {r.title || 'Untitled Presentation'}
                </h3>

                {/* Date */}
                <div className="mt-2 flex items-center gap-1.5 text-[11px] text-[#888A90]">
                  <Calendar size={12} />
                  <span>
                    {r.updated_at
                      ? new Date(r.updated_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })
                      : 'Recently updated'}
                  </span>
                </div>
              </div>

              {/* Bottom Actions */}
              <div className="mt-5 flex items-center justify-between border-t border-white/[0.08] pt-3">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={(e) => handleDownload(e, r, 'pptx')}
                    title="Download PPTX"
                    className="liquid-glass-btn flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium text-[#F4E6D3] cursor-pointer"
                  >
                    <Download size={11} /> PPTX
                  </button>
                  <button
                    onClick={(e) => handleDownload(e, r, 'pdf')}
                    title="Download PDF"
                    className="liquid-glass-btn flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium text-[#F4E6D3] cursor-pointer"
                  >
                    <Download size={11} /> PDF
                  </button>
                </div>
                <span className="flex items-center gap-1 text-xs font-semibold text-[#F28C28] group-hover:text-[#DFA36D] transition-colors">
                  <span>Open</span>
                  <ChevronRight size={13} />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function AudienceWindow({ presentationId, initialSlide = 0 }) {
  const [presentation, setPresentation] = useState(null)
  const [slideIdx, setSlideIdx] = useState(initialSlide)

  useEffect(() => {
    api.presentation(presentationId).then(setPresentation).catch(() => {})
  }, [presentationId])

  useEffect(() => {
    let channel
    try {
      channel = new BroadcastChannel('sm_presenter_channel')
      channel.onmessage = (e) => {
        if (e.data?.type === 'SLIDE_CHANGE' && typeof e.data.index === 'number') {
          setSlideIdx(e.data.index)
        }
      }
    } catch {}
    return () => {
      try {
        channel?.close()
      } catch {}
    }
  }, [])

  if (!presentation) {
    return (
      <div className="fixed inset-0 bg-[#101114] flex items-center justify-center text-xs font-mono text-[#888A90]">
        Connecting audience screen to presenter…
      </div>
    )
  }

  const slides = presentation.slides || []
  const currentSlide = slides[Math.min(slideIdx, slides.length - 1)]
  const themeId = presentation.settings?.theme || 'swiss_minimal'
  const design = getDesignSystemById(themeId)

  return (
    <div className="fixed inset-0 bg-[#101114] flex items-center justify-center p-0 select-none overflow-hidden">
      <div className="w-full h-full flex items-center justify-center p-4 md:p-8">
        <div className="w-full max-w-7xl shadow-2xl rounded-2xl overflow-hidden border border-white/10">
          <SlideView
            slide={currentSlide}
            themeId={themeId}
            designSystem={design}
            first={slideIdx === 0}
          />
        </div>
      </div>
    </div>
  )
}

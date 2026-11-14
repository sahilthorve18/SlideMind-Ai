import { useEffect, useState, useCallback } from 'react'
import {
  Activity,
  ArrowLeft,
  ExternalLink,
  FileDown,
  Layers,
  Loader2,
  MessageSquare,
  Mic,
  Sparkles,
  Upload,
  X,
  Play,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Maximize2,
  Copy,
  Trash2,
  Check,
  Palette,
  Layout,
  Wand2,
  Plus,
  Edit3,
} from 'lucide-react'
import SlideView from '../components/SlideView'
import PresenterModal from '../components/PresenterModal'
import IntelligencePanel from '../components/IntelligencePanel'
import RehearsalView from '../components/RehearsalView'
import VisualAssetEditor from '../components/VisualAssetEditor'
import { api } from '../services/api'
import { triggerFileDownload } from '../utils/download'
import { useApp } from '../context/AppContext'
import { DESIGN_SYSTEMS, getDesignSystemById } from '../services/designSystems'

const label = (s) => s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

const LAYOUT_OPTIONS = [
  { id: 'cards_hierarchy', label: 'Key Pillars / 3 Cards' },
  { id: 'stats_kpi', label: 'Traction / KPI Metrics' },
  { id: 'problem_solution', label: 'Problem vs Solution' },
  { id: 'process_diagram', label: 'Process Steps / Flow' },
  { id: 'timeline', label: 'Milestones / Timeline' },
  { id: 'quote_testimonial', label: 'Editorial Quote / Callout' },
  { id: 'split_screen', label: 'Split Screen' },
  { id: 'full_bleed_hero', label: 'Hero Cover' },
]

export default function Workspace({ presentationId, onBack, onEditInChat }) {
  const { user, toast, setActivePresentationId, presentationsVersion, activeJobId } = useApp()
  const [p, setP] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [idx, setIdx] = useState(0)
  const [busy, setBusy] = useState('')
  const [source, setSource] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [tab, setTab] = useState('slides') // 'slides' | 'intelligence' | 'rehearsal'
  const [presenting, setPresenting] = useState(false)
  const [presentTimer, setPresentTimer] = useState(0)

  // In-Slide & Studio Editing States
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [editingSlide, setEditingSlide] = useState(false)
  const [editDraft, setEditDraft] = useState({
    title: '',
    tagline: '',
    speaker_notes: '',
    bullets: [''],
  })

  const load = () => {
    setLoadError(null)
    api
      .presentation(presentationId)
      .then((data) => {
        setP(data)
        setActivePresentationId?.(data.id)
      })
      .catch((e) => {
        setLoadError(e.message || 'Could not load presentation.')
        toast(e.message, 'error')
      })
  }

  useEffect(() => {
    load()
  }, [presentationId, presentationsVersion])

  useEffect(() => {
    if (!activeJobId) return
    const interval = setInterval(() => {
      api.jobStatus(activeJobId).then((j) => {
        if (j.status === 'done' || j.status === 'failed') {
          load()
        }
      }).catch(() => {})
    }, 2500)
    return () => clearInterval(interval)
  }, [activeJobId])

  // Fullscreen Presenter Mode keyboard navigation
  useEffect(() => {
    if (!presenting) return
    const timer = setInterval(() => setPresentTimer((t) => t + 1), 1000)
    const handleKey = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault()
        setIdx((i) => Math.min((p?.slides?.length || 1) - 1, i + 1))
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault()
        setIdx((i) => Math.max(0, i - 1))
      } else if (e.key === 'Escape') {
        setPresenting(false)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => {
      clearInterval(timer)
      window.removeEventListener('keydown', handleKey)
    }
  }, [presenting, p?.slides?.length])

  if (loadError) {
    return (
      <div className="flex flex-col h-full items-center justify-center p-8 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-red-500/15 border border-red-500/30 text-red-400 flex items-center justify-center">
          <X size={24} />
        </div>
        <div>
          <h3 className="text-base font-semibold text-[#F4E6D3]">Presentation Not Found</h3>
          <p className="text-xs text-[#888A90] max-w-sm mt-1">{loadError}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={onBack}
            className="liquid-glass-btn rounded-full px-4 py-2 text-xs font-semibold text-[#F4E6D3] transition cursor-pointer"
          >
            Back to Presentations
          </button>
          <button
            onClick={load}
            className="liquid-glass-btn-primary rounded-full px-4 py-2 text-xs font-semibold text-[#101114] transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!p)
    return (
      <div className="flex h-full items-center justify-center text-xs font-mono text-[#888A90]">
        <Loader2 className="animate-spin text-brand-600" size={28} />
      </div>
    )

  const slide = p.slides[Math.min(idx, p.slides.length - 1)]
  const currentThemeId = p.settings?.theme || 'swiss_minimal'
  const currentDesign = getDesignSystemById(currentThemeId)
  const published = Boolean(p.google_url)
  const sources = Object.entries(slide?.content?.sources || {})
  const unsupported = (slide?.content?.bullets || []).filter(
    (b) => !(b.source_ids || []).length
  ).length

  const run = async (key, fn) => {
    setBusy(key)
    try {
      await fn()
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setBusy('')
    }
  }

  const changeTheme = (newThemeId) =>
    run('theme', async () => {
      await api.setTheme(p.id, newThemeId)
      await load()
      toast(`Design System updated to ${label(newThemeId)}.`, 'success')
    })

  const publish = () =>
    run('publish', async () => {
      const res = await api.publishPresentation(p.id)
      setWarnings(
        (res.not_rendered || []).map(
          (n) => `Slide ${n.slide}: ${n.what} ${n.reason}`
        )
      )
      await load()
      toast('Published to Google Slides successfully.', 'success')
    })

  const download = (fmt) =>
    run(fmt, async () => {
      let blob
      try {
        blob = await api.downloadPresentation(p.id, fmt)
      } catch {
        blob = await api.exportPresentation(p.id, fmt)
      }
      triggerFileDownload(blob, p.title, fmt)
      toast(`${fmt.toUpperCase()} download initiated!`, 'success')
    })

  const regenerateCurrentSlide = () =>
    run('regenerate', async () => {
      if (!slide) return
      await api.regenerateSlide(p.id, slide.position)
      await load()
      toast(`Slide ${slide.position} redesigned with modern visual layout.`, 'success')
    })

  const applyCustomLayout = (newLayout) =>
    run('makeover', async () => {
      if (!slide) return
      await api.regenerateSlide(p.id, slide.position, { layout: newLayout })
      await load()
      toast(`Slide ${slide.position} transformed into ${label(newLayout)}.`, 'success')
    })

  const autoOptimize = () =>
    run('audit', async () => {
      const res = await api.autoCorrectPresentation(p.id)
      await load()
      toast(
        `Design optimized! Score: ${res.audit_after?.score}/100 (${res.audit_after?.grade})`,
        'success'
      )
    })

  const formatTimer = (secs) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  const openSlideEditor = () => {
    if (!slide) return
    const bullets = (slide.content?.bullets || []).map((b) =>
      typeof b === 'object' ? b.text : String(b)
    )
    let bulletList = bullets
    if (!bulletList.length && slide.content?.spec?.blocks) {
      for (const b of slide.content.spec.blocks) {
        if (b.type === 'bullets' && Array.isArray(b.items)) {
          bulletList = b.items
          break
        } else if (b.type === 'cards' && Array.isArray(b.items)) {
          bulletList = b.items.map((i) => i.title + (i.body ? `: ${i.body}` : ''))
          break
        }
      }
    }
    setEditDraft({
      title: slide.title || '',
      tagline: slide.content?.tagline || slide.content?.spec?.tagline || '',
      speaker_notes: slide.speaker_notes || '',
      bullets: bulletList.length ? bulletList : [''],
    })
    setEditingSlide(true)
  }

  const saveSlideEdit = () =>
    run('edit_slide', async () => {
      if (!slide) return
      const cleanBullets = editDraft.bullets.map((b) => b.trim()).filter(Boolean)
      const res = await api.editPresentation({
        presentation_id: p.id,
        action: 'edit_slide',
        slide_position: slide.position,
        title: editDraft.title.trim(),
        tagline: editDraft.tagline.trim(),
        speaker_notes: editDraft.speaker_notes.trim(),
        bullets: cleanBullets,
      })
      if (res?.slides) {
        setP((prev) => ({ ...prev, ...res }))
      } else {
        await load()
      }
      setEditingSlide(false)
      toast('Slide updated successfully.', 'success')
    })

  const addSlide = () =>
    run('add_slide', async () => {
      const targetPos = idx + 2
      const res = await api.editPresentation({
        presentation_id: p.id,
        action: 'add_slide',
        slide_position: targetPos,
        title: `Slide ${targetPos}`,
        bullets: ['Key takeaway 1', 'Key takeaway 2', 'Key takeaway 3'],
      })
      if (res?.slides) {
        setP((prev) => ({ ...prev, ...res }))
        setIdx(targetPos - 1)
      } else {
        await load()
        setIdx(targetPos - 1)
      }
      toast(`Added new Slide ${targetPos}.`, 'success')
    })

  const duplicateSlide = () =>
    run('duplicate_slide', async () => {
      if (!slide) return
      const res = await api.editPresentation({
        presentation_id: p.id,
        action: 'duplicate_slide',
        slide_position: slide.position,
      })
      if (res?.slides) {
        setP((prev) => ({ ...prev, ...res }))
        setIdx((i) => i + 1)
      } else {
        await load()
        setIdx((i) => i + 1)
      }
      toast(`Slide ${slide.position} duplicated.`, 'success')
    })

  const deleteSlide = () => {
    if (p.slides.length <= 1) {
      toast('Cannot delete the only slide.', 'warning')
      return
    }
    if (!window.confirm(`Delete Slide ${slide.position}: "${slide.title}"?`)) return
    run('delete_slide', async () => {
      const res = await api.editPresentation({
        presentation_id: p.id,
        action: 'delete_slide',
        slide_position: slide.position,
      })
      if (res?.slides) {
        setP((prev) => ({ ...prev, ...res }))
        setIdx((i) => Math.max(0, Math.min(i, res.slides.length - 1)))
      } else {
        await load()
        setIdx((i) => Math.max(0, i - 1))
      }
      toast('Slide deleted.', 'success')
    })
  }

  const moveSlide = (direction) =>
    run('move_slide', async () => {
      if (!slide) return
      const fromPos = slide.position
      const toPos = direction === 'up' ? fromPos - 1 : fromPos + 1
      if (toPos < 1 || toPos > p.slides.length) return
      const res = await api.editPresentation({
        presentation_id: p.id,
        action: 'reorder_slide',
        from_position: fromPos,
        to_position: toPos,
      })
      if (res?.slides) {
        setP((prev) => ({ ...prev, ...res }))
        setIdx(toPos - 1)
      } else {
        await load()
        setIdx(toPos - 1)
      }
      toast(`Slide moved ${direction}.`, 'success')
    })

  const saveTitle = () =>
    run('update_title', async () => {
      if (!titleDraft.trim()) return
      const res = await api.editPresentation({
        presentation_id: p.id,
        action: 'update_title',
        title: titleDraft.trim(),
      })
      if (res?.title) {
        setP((prev) => ({ ...prev, title: res.title }))
      } else {
        await load()
      }
      setEditingTitle(false)
      toast('Presentation title updated.', 'success')
    })

  const btn =
    'liquid-glass-btn flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium text-[#F4E6D3] disabled:opacity-40 transition cursor-pointer'

  return (
    <div className="flex h-full min-w-0 flex-col bg-transparent">
      {/* Studio Header Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 border-b border-white/[0.08] bg-[#101114]/90 backdrop-blur-2xl px-3 sm:px-4 py-2 sm:py-2.5 shadow-sm">
        <div className="flex items-center justify-between sm:justify-start gap-2.5">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <button
              onClick={onBack}
              aria-label="Back to presentations"
              className="rounded-lg p-1.5 text-[#C5C0B8] hover:bg-white/[0.08] shrink-0 transition-colors"
            >
              <ArrowLeft size={16} />
            </button>
            <div className="min-w-0">
              {editingTitle ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={titleDraft}
                    onChange={(e) => setTitleDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveTitle()
                      if (e.key === 'Escape') setEditingTitle(false)
                    }}
                    autoFocus
                    className="rounded-lg border border-[#F28C28] bg-[#17191E] px-2 py-0.5 text-xs font-bold text-[#F4E6D3] outline-none"
                  />
                  <button
                    onClick={saveTitle}
                    disabled={busy === 'update_title'}
                    className="liquid-glass-btn-primary rounded-md px-2.5 py-0.5 text-[11px] font-semibold text-[#101114] cursor-pointer"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingTitle(false)}
                    className="rounded-md p-1 text-[#888A90] hover:text-[#F4E6D3]"
                  >
                    <X size={12} />
                  </button>
                </div>
              ) : (
                <div className="group flex items-center gap-1.5">
                  <h1 className="max-w-xs sm:max-w-md truncate text-xs sm:text-sm font-bold text-[#F4E6D3]">
                    {p.title}
                  </h1>
                  <button
                    onClick={() => {
                      setTitleDraft(p.title)
                      setEditingTitle(true)
                    }}
                    title="Rename presentation"
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 text-[#888A90] hover:text-[#F28C28]"
                  >
                    <Edit3 size={12} />
                  </button>
                </div>
              )}
              <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-[11px] text-[#888A90]">
                <span>{p.slides.length} Slides</span>
                <span>•</span>
                <span className="font-medium text-[#F28C28] truncate">
                  {currentDesign.name}
                </span>
              </div>
            </div>
          </div>

          {/* Mobile Studio View Switcher */}
          <div className="flex sm:hidden rounded-lg bg-white/[0.04] border border-white/[0.08] p-0.5 shrink-0">
            <button
              onClick={() => setTab('slides')}
              className={`p-1.5 rounded-md text-[11px] font-semibold transition ${
                tab === 'slides'
                  ? 'liquid-glass-pill-active text-[#F4E6D3]'
                  : 'text-[#C5C0B8]'
              }`}
              title="Canvas"
            >
              <Layers size={13} />
            </button>
            <button
              onClick={() => setTab('intelligence')}
              className={`p-1.5 rounded-md text-[11px] font-semibold transition ${
                tab === 'intelligence'
                  ? 'liquid-glass-pill-active text-[#F4E6D3]'
                  : 'text-[#C5C0B8]'
              }`}
              title="Audit"
            >
              <Activity size={13} />
            </button>
            <button
              onClick={() => setTab('rehearsal')}
              className={`p-1.5 rounded-md text-[11px] font-semibold transition ${
                tab === 'rehearsal'
                  ? 'liquid-glass-pill-active text-[#F4E6D3]'
                  : 'text-[#C5C0B8]'
              }`}
              title="Rehearsal"
            >
              <Mic size={13} />
            </button>
          </div>
        </div>

        {/* Desktop Studio View Switcher */}
        <div className="hidden sm:flex rounded-xl bg-white/[0.04] border border-white/[0.08] p-0.5 shadow-inner">
          <button
            onClick={() => setTab('slides')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition cursor-pointer ${
              tab === 'slides'
                ? 'liquid-glass-pill-active text-[#F4E6D3]'
                : 'text-[#C5C0B8] hover:text-[#F4E6D3]'
            }`}
          >
            <Layers size={13} /> Canvas
          </button>
          <button
            onClick={() => setTab('intelligence')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition cursor-pointer ${
              tab === 'intelligence'
                ? 'liquid-glass-pill-active text-[#F4E6D3]'
                : 'text-[#C5C0B8] hover:text-[#F4E6D3]'
            }`}
          >
            <Activity size={13} /> Audit
          </button>
          <button
            onClick={() => setTab('rehearsal')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition cursor-pointer ${
              tab === 'rehearsal'
                ? 'liquid-glass-pill-active text-[#F4E6D3]'
                : 'text-[#C5C0B8] hover:text-[#F4E6D3]'
            }`}
          >
            <Mic size={13} /> Rehearsal
          </button>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {activeJobId && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#F28C28]/15 border border-[#F28C28]/35 text-[#F28C28] text-xs font-mono animate-pulse shrink-0">
              <Loader2 size={12} className="animate-spin" />
              <span>AI updating presentation…</span>
            </div>
          )}
          {/* Presenter Fullscreen Button */}
          <button
            onClick={() => {
              setPresentTimer(0)
              setPresenting(true)
            }}
            className="liquid-glass-btn-primary flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold text-[#101114] cursor-pointer"
          >
            <Play size={12} fill="currentColor" /> Present
          </button>

          {/* Edit in Chat */}
          <button
            className={btn}
            onClick={() => onEditInChat({ id: p.id, title: p.title })}
          >
            <MessageSquare size={13} /> Chat Assist
          </button>

          {/* Downloads */}
          <button
            className={btn}
            disabled={busy === 'pptx'}
            onClick={() => download('pptx')}
            title="Download native PowerPoint (.pptx)"
          >
            {busy === 'pptx' ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <FileDown size={13} />
            )}
            PPTX
          </button>
          <button
            className={btn}
            disabled={busy === 'pdf'}
            onClick={() => download('pdf')}
            title="Download high-resolution PDF (.pdf)"
          >
            {busy === 'pdf' ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <FileDown size={13} />
            )}
            PDF
          </button>

          {/* Google Slides Sync */}
          {published ? (
            <a
              className={btn}
              href={p.google_url}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={13} /> Slides Link
            </a>
          ) : (
            <button
              className={btn}
              disabled={!user?.google_connected || busy === 'publish'}
              onClick={publish}
              title={
                user?.google_connected
                  ? 'Sync presentation to your Google Drive account'
                  : 'Connect Google Slides from Settings first'
              }
            >
              {busy === 'publish' ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Upload size={13} />
              )}
              Google Slides
            </button>
          )}

          {/* Auto-Optimize Design */}
          <button
            className={btn}
            disabled={busy === 'audit'}
            onClick={autoOptimize}
            title="Run automated design quality audit and auto-correct"
          >
            {busy === 'audit' ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Wand2 size={13} />
            )}
            Audit & Optimize
          </button>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="border-b border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          <b>Notice:</b> {warnings.join('; ')}.
        </div>
      )}

      {/* Main Studio Viewport */}
      {tab === 'intelligence' ? (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-5xl">
            <IntelligencePanel
              presentationId={p.id}
              onSelectSlide={(newIdx) => {
                setIdx(newIdx)
                setTab('slides')
              }}
              onReloadPresentation={load}
            />
          </div>
        </div>
      ) : tab === 'rehearsal' ? (
        <div className="flex-1 overflow-y-auto p-6">
          <RehearsalView
            presentation={p}
            onBackToSlides={() => setTab('slides')}
          />
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col md:flex-row">
          {/* LEFT: Slide Filmstrip Navigator */}
          <div className="flex gap-2.5 overflow-x-auto border-b border-white/[0.08] bg-[#17191E]/70 backdrop-blur-xl p-3 md:w-60 md:shrink-0 md:flex-col md:overflow-y-auto md:border-b-0 md:border-r">
            <div className="hidden items-center justify-between px-1 pb-1 md:flex">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#888A90]">
                Slide Navigator ({p.slides.length})
              </span>
            </div>
            {p.slides.map((s, i) => (
              <button
                key={s.position}
                onClick={() => setIdx(i)}
                className={`group relative w-40 shrink-0 overflow-hidden rounded-xl border text-left transition-all md:w-full ${
                  i === idx
                    ? 'border-[#F28C28] ring-2 ring-[#F28C28]/30'
                    : 'border-white/[0.08] hover:border-white/[0.20]'
                }`}
              >
                <div className="pointer-events-none aspect-video w-full overflow-hidden">
                  <SlideView
                    slide={s}
                    themeId={currentThemeId}
                    designSystem={currentDesign}
                    first={i === 0}
                  />
                </div>
                <div className="flex items-center justify-between bg-[#1E2026] px-2 py-1.5">
                  <span className="truncate text-[11px] font-medium text-[#F4E6D3]">
                    {s.position}. {s.title}
                  </span>
                  <span className="text-[10px] text-[#888A90] uppercase">
                    {s.content?.layout?.split('_')[0] || 'std'}
                  </span>
                </div>
              </button>
            ))}

            {/* Add Slide Button in Filmstrip */}
            <button
              onClick={addSlide}
              disabled={p.slides.length >= 40 || busy === 'add_slide'}
              className="flex w-40 shrink-0 items-center justify-center gap-1.5 rounded-xl border border-dashed border-white/[0.14] p-3 text-xs font-semibold text-[#C5C0B8] hover:border-[#F28C28] hover:text-[#F28C28] md:w-full transition-colors cursor-pointer"
            >
              {busy === 'add_slide' ? (
                <Loader2 size={13} className="animate-spin text-[#F28C28]" />
              ) : (
                <Plus size={14} />
              )}
              <span>Add Slide</span>
            </button>
          </div>

          {/* CENTER: Main Slide Canvas & Notes */}
          <div className="flex min-w-0 flex-1 flex-col overflow-y-auto p-2 sm:p-4 md:p-6">
            <div className="mx-auto w-full max-w-4xl space-y-4">
              {/* Canvas Header & Stepper */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#888A90]">
                    Slide {idx + 1} of {p.slides.length}
                  </span>
                  <span className="rounded-md bg-white/[0.06] border border-white/[0.08] px-2 py-0.5 text-[10px] font-semibold text-[#C5C0B8]">
                    {label(slide?.content?.layout || 'Standard')}
                  </span>
                </div>

                {/* Stepper Buttons & Actions */}
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    disabled={idx === 0}
                    onClick={() => setIdx((i) => Math.max(0, i - 1))}
                    className="rounded-lg border border-white/[0.10] bg-white/[0.04] p-1.5 text-[#C5C0B8] hover:bg-white/[0.08] disabled:opacity-20 cursor-pointer"
                    title="Previous slide"
                  >
                    <ChevronLeft size={15} />
                  </button>
                  <button
                    disabled={idx === p.slides.length - 1}
                    onClick={() =>
                      setIdx((i) => Math.min(p.slides.length - 1, i + 1))
                    }
                    className="rounded-lg border border-white/[0.10] bg-white/[0.04] p-1.5 text-[#C5C0B8] hover:bg-white/[0.08] disabled:opacity-20 cursor-pointer"
                    title="Next slide"
                  >
                    <ChevronRight size={15} />
                  </button>

                  <div className="mx-1 h-4 w-px bg-white/[0.10]" />

                  {/* Reorder Up/Down */}
                  <button
                    disabled={idx === 0 || busy === 'move_slide'}
                    onClick={() => moveSlide('up')}
                    className="rounded-lg border border-white/[0.10] bg-white/[0.04] p-1.5 text-[#C5C0B8] hover:bg-white/[0.08] disabled:opacity-20 cursor-pointer"
                    title="Move slide up"
                  >
                    <ChevronUp size={15} />
                  </button>
                  <button
                    disabled={idx === p.slides.length - 1 || busy === 'move_slide'}
                    onClick={() => moveSlide('down')}
                    className="rounded-lg border border-white/[0.10] bg-white/[0.04] p-1.5 text-[#C5C0B8] hover:bg-white/[0.08] disabled:opacity-20 cursor-pointer"
                    title="Move slide down"
                  >
                    <ChevronDown size={15} />
                  </button>

                  <div className="mx-1 h-4 w-px bg-white/[0.10]" />

                  {/* Edit Content */}
                  <button
                    onClick={openSlideEditor}
                    className="flex items-center gap-1 rounded-lg border border-[#F28C28]/35 bg-[#F28C28]/10 px-2.5 py-1 text-xs font-semibold text-[#F28C28] hover:bg-[#F28C28]/20 cursor-pointer transition-colors"
                    title="Edit slide text and speaker notes"
                  >
                    <Edit3 size={13} />
                    <span>Edit Content</span>
                  </button>

                  {/* Duplicate Slide */}
                  <button
                    disabled={p.slides.length >= 40 || busy === 'duplicate_slide'}
                    onClick={duplicateSlide}
                    className="rounded-lg border border-white/[0.10] bg-white/[0.04] p-1.5 text-[#C5C0B8] hover:bg-white/[0.08] disabled:opacity-20 cursor-pointer"
                    title="Duplicate slide"
                  >
                    <Copy size={14} />
                  </button>

                  {/* Delete Slide */}
                  <button
                    disabled={p.slides.length <= 1 || busy === 'delete_slide'}
                    onClick={deleteSlide}
                    className="rounded-lg border border-white/[0.10] bg-white/[0.04] p-1.5 text-red-400 hover:bg-red-500/10 disabled:opacity-20 cursor-pointer"
                    title="Delete slide"
                  >
                    <Trash2 size={14} />
                  </button>

                  {/* Add Slide */}
                  <button
                    disabled={p.slides.length >= 40 || busy === 'add_slide'}
                    onClick={addSlide}
                    className="liquid-glass-btn flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold text-[#F4E6D3] cursor-pointer"
                    title="Add slide after current"
                  >
                    <Plus size={13} />
                    <span>Add Slide</span>
                  </button>
                </div>
              </div>

              {/* 16:9 Presentation Canvas */}
              {slide && (
                <div className="rounded-2xl border border-white/[0.12] bg-[#17191E] p-2 shadow-2xl">
                  <SlideView
                    slide={slide}
                    themeId={currentThemeId}
                    designSystem={currentDesign}
                    first={idx === 0}
                  />
                </div>
              )}

              {/* Speaker Notes */}
              <div className="liquid-glass-card p-4 text-xs">
                <div className="mb-2 flex items-center justify-between">
                  <div className="font-bold uppercase tracking-wider text-[#888A90]">
                    Speaker Notes & Talking Points
                  </div>
                  <button
                    onClick={openSlideEditor}
                    className="flex items-center gap-1 text-[11px] font-semibold text-[#F28C28] hover:text-[#DFA36D] cursor-pointer transition-colors"
                  >
                    <Edit3 size={11} />
                    <span>Edit Notes</span>
                  </button>
                </div>
                {slide?.speaker_notes ? (
                  <p className="leading-relaxed text-[#C5C0B8]">
                    {slide.speaker_notes}
                  </p>
                ) : (
                  <p className="text-[#888A90]">
                    No speaker notes for this slide yet. Click Edit Notes to add talking points or ask in Chat Assist.
                  </p>
                )}
              </div>

              {/* AI Disclaimer Bar */}
              <div className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-3.5 py-2 text-[11px] text-[#888A90]">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#F28C28]" />
                  <span>AI-Generated Presentation Content · Verify all data points before external delivery.</span>
                </div>
                <a href="/terms" target="_blank" rel="noreferrer" className="text-[#888A90] hover:text-[#F4E6D3] underline underline-offset-2">
                  Terms
                </a>
              </div>
            </div>
          </div>

          {/* RIGHT: Studio Design Inspector & Makeover */}
          <aside className="space-y-6 overflow-y-auto border-t border-white/[0.08] bg-[#17191E]/80 backdrop-blur-xl p-5 text-xs text-[#F4E6D3] md:w-72 md:shrink-0 md:border-l md:border-t-0">
            {/* Live Design System Switcher */}
            <div>
              <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[#888A90]">
                <Palette size={13} />
                <span>Presentation Design System</span>
              </div>
              <p className="mt-1 text-[11px] text-[#888A90]">
                Change the entire presentation’s visual philosophy on the fly
              </p>
              <select
                value={currentDesign?.id || currentThemeId}
                disabled={busy === 'theme'}
                onChange={(e) => changeTheme(e.target.value)}
                className="mt-2.5 w-full rounded-xl border border-white/[0.12] bg-[#1E2026] p-2.5 text-xs font-semibold text-[#F4E6D3] outline-none focus:border-[#F28C28]"
              >
                {DESIGN_SYSTEMS.map((ds) => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name} ({ds.category})
                  </option>
                ))}
              </select>
            </div>

            {/* AI Slide Makeover (Change Layout) */}
            <div className="border-t border-white/[0.08] pt-5">
              <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[#888A90]">
                <Layout size={13} />
                <span>Slide Makeover (Layout)</span>
              </div>
              <p className="mt-1 text-[11px] text-[#888A90]">
                Transform this individual slide into a different layout
              </p>
              <div className="mt-2.5 space-y-1.5">
                {LAYOUT_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    disabled={busy === 'makeover'}
                    onClick={() => applyCustomLayout(opt.id)}
                    className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-left font-medium transition cursor-pointer ${
                      slide?.content?.layout === opt.id
                        ? 'border-[#F28C28] bg-[#F28C28]/15 text-[#F28C28]'
                        : 'border-white/[0.08] bg-white/[0.02] text-[#C5C0B8] hover:bg-white/[0.06] hover:text-[#F4E6D3]'
                    }`}
                  >
                    <span>{opt.label}</span>
                    {slide?.content?.layout === opt.id && <Check size={13} />}
                  </button>
                ))}
              </div>
            </div>

            {/* Visual Asset Studio & Editor */}
            {slide && (
              <div className="border-t border-white/[0.08] pt-5">
                <VisualAssetEditor
                  presentationId={p.id}
                  slide={slide}
                  onSlideUpdated={load}
                />
              </div>
            )}

            {/* Verified Citations & Grounding */}
            <div className="border-t border-white/[0.08] pt-5">
              <div className="mb-2 font-bold uppercase tracking-wider text-[#888A90]">
                Grounding & Sources ({sources.length})
              </div>
              {unsupported > 0 && (
                <p className="mb-2 rounded-lg bg-[#F28C28]/15 border border-[#F28C28]/30 p-2 text-[11px] text-[#F28C28]">
                  {unsupported} point without a source.
                </p>
              )}
              {sources.length === 0 ? (
                <p className="text-[#888A90]">No external source attached.</p>
              ) : (
                sources.map(([id, s]) => (
                  <button
                    key={id}
                    onClick={() => setSource(s)}
                    className="mb-1 block w-full truncate rounded-xl border border-white/[0.08] bg-white/[0.02] p-2 text-left text-[#C5C0B8] hover:border-[#F28C28] hover:text-[#F4E6D3] transition-colors"
                  >
                    {s.filename || s.url || id}
                    {s.page_number ? ` · p.${s.page_number}` : ''}
                  </button>
                ))
              )}
            </div>
          </aside>
        </div>
      )}

      {/* ========================================================= */}
      {/* IMMERSIVE FULLSCREEN PRESENTER MODE                        */}
      {/* ========================================================= */}
      {presenting && (
        <PresenterModal
          presentation={p}
          initialSlideIndex={idx}
          onClose={() => setPresenting(false)}
        />
      )}

      {/* Source Modal */}
      {source && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          onClick={() => setSource(null)}
        >
          <div
            className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/[0.14] bg-[#17191E] p-5 text-sm text-[#F4E6D3] shadow-2xl backdrop-blur-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-1 flex items-start justify-between gap-2">
              <div className="font-semibold text-[#F4E6D3]">{source.filename || 'Source'}</div>
              <button onClick={() => setSource(null)} aria-label="Close" className="text-[#888A90] hover:text-[#F4E6D3]">
                <X size={16} />
              </button>
            </div>
            <div className="mb-3 text-xs text-[#888A90]">
              {source.page_number ? `Page ${source.page_number}` : ''}
              {source.section_heading ? ` · ${source.section_heading}` : ''}
            </div>
            <p className="whitespace-pre-wrap rounded-xl bg-[#1E2026] border border-white/[0.08] p-3 text-[#C5C0B8]">
              {source.text}
            </p>
            {source.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-block text-[#F28C28] hover:text-[#DFA36D] underline"
              >
                Open source page
              </a>
            )}
          </div>
        </div>
      )}
      {/* Slide Content Editor Modal */}
      {editingSlide && slide && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-md"
          onClick={() => setEditingSlide(false)}
        >
          <div
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/[0.14] bg-[#17191E] p-6 text-[#F4E6D3] shadow-2xl backdrop-blur-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h2 className="text-base font-bold text-[#F4E6D3]">
                  Edit Slide {slide.position}
                </h2>
                <p className="text-xs text-[#888A90]">
                  Edit title, bullets, and speaker notes with live preview update
                </p>
              </div>
              <button
                onClick={() => setEditingSlide(false)}
                className="rounded-lg p-1.5 text-[#888A90] hover:bg-white/[0.08] hover:text-[#F4E6D3]"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Title */}
              <div>
                <label className="mb-1 block font-bold uppercase tracking-wider text-[#888A90]">
                  Slide Title
                </label>
                <input
                  type="text"
                  value={editDraft.title}
                  onChange={(e) =>
                    setEditDraft((d) => ({ ...d, title: e.target.value }))
                  }
                  className="w-full rounded-xl border border-white/[0.12] bg-[#1E2026] p-2.5 text-sm font-semibold text-[#F4E6D3] outline-none focus:border-[#F28C28]"
                />
              </div>

              {/* Tagline / Subtitle */}
              <div>
                <label className="mb-1 block font-bold uppercase tracking-wider text-[#888A90]">
                  Subtitle / Tagline (Optional)
                </label>
                <input
                  type="text"
                  value={editDraft.tagline}
                  onChange={(e) =>
                    setEditDraft((d) => ({ ...d, tagline: e.target.value }))
                  }
                  placeholder="e.g. Key strategic pillars for Q3"
                  className="w-full rounded-xl border border-white/[0.12] bg-[#1E2026] p-2.5 text-xs text-[#F4E6D3] placeholder:text-[#888A90] outline-none focus:border-[#F28C28]"
                />
              </div>

              {/* Bullet Points */}
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="font-bold uppercase tracking-wider text-[#888A90]">
                    Key Points & Content ({editDraft.bullets.length})
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setEditDraft((d) => ({
                        ...d,
                        bullets: [...d.bullets, ''],
                      }))
                    }
                    className="flex items-center gap-1 text-[11px] font-semibold text-[#F28C28] hover:text-[#DFA36D] cursor-pointer"
                  >
                    <Plus size={12} />
                    Add Point
                  </button>
                </div>
                <div className="space-y-2">
                  {editDraft.bullets.map((b, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="w-5 text-right font-mono text-[11px] text-[#888A90]">
                        {i + 1}.
                      </span>
                      <input
                        type="text"
                        value={b}
                        onChange={(e) => {
                          const next = [...editDraft.bullets]
                          next[i] = e.target.value
                          setEditDraft((d) => ({ ...d, bullets: next }))
                        }}
                        placeholder="Enter point or takeaway..."
                        className="flex-1 rounded-xl border border-white/[0.12] bg-[#1E2026] p-2 text-xs text-[#F4E6D3] placeholder:text-[#888A90] outline-none focus:border-[#F28C28]"
                      />
                      <button
                        type="button"
                        disabled={editDraft.bullets.length <= 1}
                        onClick={() => {
                          setEditDraft((d) => ({
                            ...d,
                            bullets: d.bullets.filter((_, idx) => idx !== i),
                          }))
                        }}
                        className="rounded-lg p-1.5 text-[#888A90] hover:text-red-400 disabled:opacity-20 cursor-pointer"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Speaker Notes */}
              <div>
                <label className="mb-1 block font-bold uppercase tracking-wider text-[#888A90]">
                  Speaker Notes
                </label>
                <textarea
                  rows={4}
                  value={editDraft.speaker_notes}
                  onChange={(e) =>
                    setEditDraft((d) => ({
                      ...d,
                      speaker_notes: e.target.value,
                    }))
                  }
                  placeholder="Executive talking points, context, or delivery guidance..."
                  className="w-full resize-none rounded-xl border border-white/[0.12] bg-[#1E2026] p-2.5 text-xs leading-relaxed text-[#F4E6D3] placeholder:text-[#888A90] outline-none focus:border-[#F28C28]"
                />
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-2.5 border-t border-white/[0.08] pt-4">
              <button
                onClick={() => setEditingSlide(false)}
                className="liquid-glass-btn rounded-xl px-4 py-2 text-xs font-semibold text-[#C5C0B8] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={saveSlideEdit}
                disabled={busy === 'edit_slide'}
                className="liquid-glass-btn-primary flex items-center gap-1.5 rounded-xl px-5 py-2 text-xs font-semibold text-[#101114] cursor-pointer"
              >
                {busy === 'edit_slide' ? (
                  <Loader2 size={13} className="animate-spin text-[#101114]" />
                ) : (
                  <Check size={13} />
                )}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

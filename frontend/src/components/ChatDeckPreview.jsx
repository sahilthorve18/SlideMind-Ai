import { useEffect, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Play,
  ExternalLink,
  Layers,
  FileText,
  Sparkles,
  Download,
  Loader2,
  Wand2,
  BarChart3,
  AlignLeft,
} from 'lucide-react'
import SlideView from './SlideView'
import ExportModal from './ExportModal'
import { api } from '../services/api'
import { getDesignSystemById } from '../services/designSystems'
import { triggerFileDownload } from '../utils/download'
import { useApp } from '../context/AppContext'

export default function ChatDeckPreview({
  presentationId,
  onOpenPresent,
  onOpenWorkspace,
  onQuickPrompt,
}) {
  const { presentationsVersion } = useApp() || {}
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isUpdating, setIsUpdating] = useState(false)
  const [error, setError] = useState(null)
  const [idx, setIdx] = useState(0)
  const [showNotes, setShowNotes] = useState(false)
  const [exportModalOpen, setExportModalOpen] = useState(false)

  useEffect(() => {
    if (!presentationId) return
    let active = true
    if (!data) {
      setLoading(true)
    } else {
      setIsUpdating(true)
    }
    setError(null)
    api
      .presentation(presentationId)
      .then((res) => {
        if (active) {
          setData(res)
          setLoading(false)
          setIsUpdating(false)
          if (res?.slides?.length) {
            setIdx((prev) => Math.min(prev, res.slides.length - 1))
          }
        }
      })
      .catch((err) => {
        if (active) {
          if (!data) {
            setError(err.message || 'Could not load slide deck preview.')
          }
          setLoading(false)
          setIsUpdating(false)
        }
      })
    return () => {
      active = false
    }
  }, [presentationId, presentationsVersion])

  if (loading) {
    return (
      <div className="my-4 flex items-center justify-center rounded-2xl border border-white/10 bg-white/[0.02] p-8 text-xs text-outline font-mono gap-2 backdrop-blur-md">
        <Loader2 size={16} className="animate-spin text-primary" />
        <span>Rendering architectural slide canvas…</span>
      </div>
    )
  }

  if (error || !data || !data.slides?.length) {
    return null
  }

  const slides = data.slides
  const currentSlide = slides[Math.min(idx, slides.length - 1)]
  const themeId = data.settings?.theme || 'swiss_minimal'
  const design = getDesignSystemById(themeId)

  const handleDownload = async (fmt) => {
    setDownloading(true)
    try {
      let blob
      try {
        blob = await api.downloadPresentation(data.id, fmt)
      } catch {
        blob = await api.exportPresentation(data.id, fmt)
      }
      triggerFileDownload(blob, data.title, fmt)
    } catch {
      // quiet failover
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="my-4 rounded-2xl border border-white/[0.14] bg-[#0c0c0e]/95 p-4 md:p-5 shadow-[0_20px_50px_rgba(0,0,0,0.5)] backdrop-blur-xl">
      {/* Deck Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3.5 border-b border-white/[0.08]">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
            <Layers size={15} />
          </div>
          <div className="min-w-0">
            <h4 className="font-medium text-sm text-white truncate max-w-xs md:max-w-md">
              {data.title || 'Architectural Presentation'}
            </h4>
            <div className="flex items-center gap-2 text-[11px] text-zinc-400 font-mono">
              <span>{slides.length} slides</span>
              <span>•</span>
              <span className="uppercase text-primary/80">{design?.name || themeId}</span>
              {isUpdating && (
                <>
                  <span>•</span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-[#F28C28]/15 px-2 py-0.5 text-[10px] font-mono text-[#F28C28] border border-[#F28C28]/30 animate-pulse">
                    <Loader2 size={10} className="animate-spin" />
                    <span>Updating slides…</span>
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpenPresent?.(data, idx)}
            className="flex items-center gap-1.5 rounded-full liquid-glass-btn-primary px-3 py-1.5 text-xs font-semibold text-[#101114] cursor-pointer shadow-md transition-all active:scale-95"
          >
            <Play size={12} fill="currentColor" />
            <span>Present</span>
          </button>

          <button
            onClick={() => onOpenWorkspace?.(data.id)}
            className="flex items-center gap-1.5 rounded-full liquid-glass-btn px-3 py-1.5 text-xs font-medium text-[#F4E6D3] hover:text-white cursor-pointer transition-colors"
          >
            <span>Edit Workspace</span>
            <ExternalLink size={12} />
          </button>

          <button
            onClick={() => setExportModalOpen(true)}
            className="flex items-center gap-1.5 rounded-full liquid-glass-btn px-3 py-1.5 text-xs font-medium text-[#F4E6D3] hover:text-[#F28C28] cursor-pointer transition-colors"
            title="Export Options (PPTX / PDF)"
          >
            <Download size={13} />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Slide Preview Canvas */}
      <div className="relative mt-3.5 w-full rounded-xl overflow-hidden border border-white/[0.12] shadow-xl group">
        <SlideView
          slide={currentSlide}
          themeId={themeId}
          designSystem={design}
          first={idx === 0}
        />

        {/* Hover Slide Nav Buttons */}
        <button
          disabled={idx === 0}
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
          className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/60 border border-white/20 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-0 hover:bg-black/80 cursor-pointer shadow-lg"
          title="Previous Slide"
        >
          <ChevronLeft size={16} />
        </button>
        <button
          disabled={idx === slides.length - 1}
          onClick={() => setIdx((i) => Math.min(slides.length - 1, i + 1))}
          className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/60 border border-white/20 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-0 hover:bg-black/80 cursor-pointer shadow-lg"
          title="Next Slide"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Slide Controls Bar */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <button
            disabled={idx === 0}
            onClick={() => setIdx((i) => Math.max(0, i - 1))}
            className="rounded-md border border-white/10 bg-white/[0.03] p-1 text-zinc-300 hover:text-white hover:bg-white/[0.08] disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="font-mono text-zinc-300 px-1">
            Slide {idx + 1} of {slides.length}
          </span>
          <button
            disabled={idx === slides.length - 1}
            onClick={() => setIdx((i) => Math.min(slides.length - 1, i + 1))}
            className="rounded-md border border-white/10 bg-white/[0.03] p-1 text-zinc-300 hover:text-white hover:bg-white/[0.08] disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
          >
            <ChevronRight size={14} />
          </button>
        </div>

        {/* Thumbnail Selector Dots */}
        <div className="flex items-center gap-1">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setIdx(i)}
              className={`h-1.5 rounded-full transition-all cursor-pointer ${
                i === idx ? 'w-4 bg-primary' : 'w-1.5 bg-white/20 hover:bg-white/40'
              }`}
              title={`Slide ${i + 1}`}
            />
          ))}
        </div>

        {/* Speaker Notes Toggle */}
        <button
          onClick={() => setShowNotes(!showNotes)}
          className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
            showNotes
              ? 'bg-primary/20 text-primary border border-primary/30'
              : 'text-zinc-400 hover:text-white hover:bg-white/[0.05]'
          }`}
        >
          <FileText size={12} />
          <span>Speaker Notes</span>
        </button>
      </div>

      {/* Speaker Notes Drawer */}
      {showNotes && (
        <div className="mt-3 rounded-xl border border-white/[0.08] bg-white/[0.02] p-3.5 text-xs text-zinc-300 leading-relaxed font-sans">
          <div className="text-[10px] uppercase font-mono text-primary/80 mb-1 tracking-wider">
            Speaker Script (Slide {idx + 1})
          </div>
          {currentSlide?.speaker_notes ? (
            <p className="whitespace-pre-wrap">{currentSlide.speaker_notes}</p>
          ) : (
            <p className="text-zinc-500 italic">No speaker notes provided for this slide.</p>
          )}
        </div>
      )}

      {/* Quick AI Micro-Action Chips */}
      <div className="mt-3.5 pt-3 border-t border-white/[0.08] flex items-center gap-2 overflow-x-auto pb-1 text-xs scrollbar-none">
        <span className="text-[11px] text-[#888A90] font-mono flex items-center gap-1 shrink-0">
          <Sparkles size={11} className="text-[#F28C28]" />
          <span>Quick polish:</span>
        </span>

        <button
          onClick={() =>
            onQuickPrompt?.(`Make slide ${idx + 1} ("${currentSlide?.title}") more visual with dynamic cards or stats.`)
          }
          className="shrink-0 flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.08] hover:border-[#F28C28]/40 transition-colors cursor-pointer text-[11px]"
        >
          <Wand2 size={11} className="text-[#F28C28]" />
          <span>Make slide {idx + 1} more visual</span>
        </button>

        <button
          onClick={() =>
            onQuickPrompt?.(`Add an interactive data metric chart to slide ${idx + 1} ("${currentSlide?.title}").`)
          }
          className="shrink-0 flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.08] hover:border-[#F28C28]/40 transition-colors cursor-pointer text-[11px]"
        >
          <BarChart3 size={11} className="text-[#DFA36D]" />
          <span>Add metric chart</span>
        </button>

        <button
          onClick={() =>
            onQuickPrompt?.(`Insert a 2x2 competitive positioning matrix slide comparing key competitors.`)
          }
          className="shrink-0 flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.08] hover:border-[#F28C28]/40 transition-colors cursor-pointer text-[11px]"
        >
          <Layers size={11} className="text-[#F28C28]" />
          <span>Add competitor matrix</span>
        </button>

        <button
          onClick={() =>
            onQuickPrompt?.(`Add a quarterly milestone roadmap slide showing execution horizon for next 12 months.`)
          }
          className="shrink-0 flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.08] hover:border-[#F28C28]/40 transition-colors cursor-pointer text-[11px]"
        >
          <Sparkles size={11} className="text-[#DFA36D]" />
          <span>Add milestone roadmap</span>
        </button>

        <button
          onClick={() =>
            onQuickPrompt?.(`Write engaging speaker notes and talking cues for slide ${idx + 1} ("${currentSlide?.title}").`)
          }
          className="shrink-0 flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.08] hover:border-[#F28C28]/40 transition-colors cursor-pointer text-[11px]"
        >
          <AlignLeft size={11} className="text-[#F4E6D3]" />
          <span>Write speaker notes</span>
        </button>
      </div>

      {/* AI-Generated Content Disclaimer */}
      <div className="mt-3 pt-2.5 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-[#888A90] font-sans">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#F28C28]/80" />
          <span>AI-Generated Presentation · Verify factual claims, metrics, and dates before professional distribution.</span>
        </span>
        <a href="/terms" target="_blank" rel="noreferrer" className="hover:text-[#F4E6D3] underline underline-offset-2 transition-colors">
          Terms & Disclaimers
        </a>
      </div>

      {/* Export Customizer Modal */}
      <ExportModal
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        presentation={data}
      />
    </div>
  )
}

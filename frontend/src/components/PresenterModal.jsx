import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  Maximize2,
  Minimize2,
  ChevronLeft,
  ChevronRight,
  X,
  Play,
  Pause,
  RotateCcw,
  Clock,
  Tv,
  FileText,
  Layers,
  ExternalLink,
} from 'lucide-react'
import SlideView from './SlideView'
import { getDesignSystemById } from '../services/designSystems'
import { useApp } from '../context/AppContext'

export default function PresenterModal({
  presentation,
  initialSlideIndex = 0,
  onClose,
}) {
  const { setIsPresenting, toast } = useApp()
  const [idx, setIdx] = useState(initialSlideIndex)
  const [viewMode, setViewMode] = useState('presenter') // 'audience' | 'presenter'
  const [seconds, setSeconds] = useState(0)
  const [timerRunning, setTimerRunning] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const broadcastRef = useRef(null)

  useEffect(() => {
    try {
      broadcastRef.current = new BroadcastChannel('sm_presenter_channel')
    } catch {}
    return () => {
      try {
        broadcastRef.current?.close()
      } catch {}
    }
  }, [])

  // Notify AppContext that we are in presentation mode so FloatingNavigation hides
  useEffect(() => {
    setIsPresenting?.(true)
    return () => {
      setIsPresenting?.(false)
    }
  }, [setIsPresenting])

  const slides = presentation?.slides || []
  const totalSlides = slides.length
  const currentSlide = slides[Math.min(idx, totalSlides - 1)]
  const nextSlide = idx + 1 < totalSlides ? slides[idx + 1] : null
  const currentThemeId = presentation?.settings?.theme || 'swiss_minimal'
  const currentDesign = getDesignSystemById(currentThemeId)

  useEffect(() => {
    if (broadcastRef.current) {
      broadcastRef.current.postMessage({
        type: 'SLIDE_CHANGE',
        index: idx,
        total: totalSlides,
        title: presentation?.title,
      })
    }
  }, [idx, totalSlides, presentation?.title])

  const openAudienceWindow = () => {
    try {
      const popup = window.open(
        `/presentations/${presentation.id}?view=audience&slide=${idx}`,
        'SlideMindAudienceWindow',
        'width=1280,height=720,menubar=no,toolbar=no,location=no'
      )
      if (!popup) {
        toast('Popup was blocked. Please allow popups to open the projector window.', 'info')
      } else {
        toast('Audience screen opened. Move it to your projector or external display!', 'success')
      }
    } catch (e) {
      toast('Could not open external window: ' + e.message, 'error')
    }
  }

  // Timer tick
  useEffect(() => {
    if (!timerRunning) return
    const interval = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(interval)
  }, [timerRunning])

  const formatTime = (totalSec) => {
    const mins = Math.floor(totalSec / 60)
    const secs = totalSec % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault()
        setIdx((i) => Math.min(totalSlides - 1, i + 1))
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault()
        setIdx((i) => Math.max(0, i - 1))
      } else if (e.key === 'Escape') {
        onClose?.()
      } else if (e.key === 't' || e.key === 'T') {
        setViewMode((m) => (m === 'audience' ? 'presenter' : 'audience'))
      } else if (e.key === 'f' || e.key === 'F') {
        toggleFullscreen()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [totalSlides, onClose])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {})
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {})
    }
  }

  if (!presentation || totalSlides === 0) return null

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex flex-col bg-[#101114] text-[#F4E6D3] select-none overflow-hidden">
      {/* Top Bar Navigation */}
      <header className="flex h-14 items-center justify-between border-b border-white/[0.08] bg-[#101114]/80 px-3 sm:px-6 backdrop-blur-xl">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F28C28] animate-pulse shrink-0" />
            <span className="font-semibold text-xs sm:text-sm text-[#F4E6D3] truncate max-w-[130px] sm:max-w-sm">
              {presentation.title || 'Live Presentation'}
            </span>
          </div>
          <span className="rounded-full bg-white/[0.06] border border-white/[0.1] px-2 py-0.5 text-[10px] sm:text-xs font-mono text-[#888A90] shrink-0">
            {idx + 1} / {totalSlides}
          </span>
        </div>

        {/* View Mode Switcher & Tools */}
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-white/[0.08] bg-white/[0.03] p-0.5 text-xs">
            <button
              onClick={() => setViewMode('audience')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors cursor-pointer ${
                viewMode === 'audience'
                  ? 'bg-[#F28C28]/20 text-[#F28C28] border border-[#F28C28]/30 shadow-sm'
                  : 'text-[#888A90] hover:text-[#F4E6D3]'
              }`}
            >
              <Tv size={14} />
              <span>Audience View</span>
            </button>
            <button
              onClick={() => setViewMode('presenter')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors cursor-pointer ${
                viewMode === 'presenter'
                  ? 'bg-[#F28C28]/20 text-[#F28C28] border border-[#F28C28]/30 shadow-sm'
                  : 'text-[#888A90] hover:text-[#F4E6D3]'
              }`}
            >
              <FileText size={14} />
              <span>Presenter View</span>
            </button>
          </div>

          <button
            onClick={openAudienceWindow}
            className="hidden sm:flex items-center gap-1 rounded-lg border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-xs text-[#888A90] hover:text-[#F28C28] hover:bg-white/[0.08] transition-colors cursor-pointer"
            title="Pop out audience window to projector or external monitor"
          >
            <ExternalLink size={13} />
            <span>Audience Screen</span>
          </button>

          <button
            onClick={toggleFullscreen}
            className="rounded-lg border border-white/[0.08] bg-white/[0.04] p-1.5 text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/[0.08] transition-colors cursor-pointer"
            title="Toggle Fullscreen (F)"
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>

          <button
            onClick={onClose}
            className="rounded-lg border border-white/[0.08] bg-white/[0.04] p-1.5 text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/[0.08] transition-colors cursor-pointer"
            title="Exit (Esc)"
          >
            <X size={16} />
          </button>
        </div>
      </header>

      {/* Main Canvas Body */}
      <div className="flex flex-1 items-center justify-center p-4 md:p-6 overflow-hidden">
        {viewMode === 'audience' ? (
          /* AUDIENCE VIEW: Pure 16:9 Canvas */
          <div className="relative flex h-full w-full max-w-6xl items-center justify-center">
            <div className="w-full shadow-2xl rounded-2xl overflow-hidden border border-white/10">
              <SlideView
                slide={currentSlide}
                themeId={currentThemeId}
                designSystem={currentDesign}
                first={idx === 0}
              />
            </div>
          </div>
        ) : (
          /* PRESENTER VIEW: Dual Stage + Timer + Speaker Notes */
          <div className="flex flex-col lg:grid h-full w-full max-w-7xl lg:grid-cols-12 gap-4 lg:gap-6 items-stretch overflow-y-auto lg:overflow-hidden">
            {/* Left: Main Live Slide */}
            <div className="w-full lg:col-span-8 flex flex-col justify-center shrink-0">
              <div className="relative w-full rounded-2xl overflow-hidden border border-white/15 shadow-[0_20px_60px_rgba(0,0,0,0.8)]">
                <SlideView
                  slide={currentSlide}
                  themeId={currentThemeId}
                  designSystem={currentDesign}
                  first={idx === 0}
                />
              </div>
            </div>

            {/* Right: Speaker Teleprompter, Next Slide & Timer */}
            <div className="w-full lg:col-span-4 flex flex-col gap-4 overflow-hidden">
              {/* Timer & Controls */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4 backdrop-blur-md">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5 text-xs text-[#888A90] font-mono">
                    <Clock size={14} className="text-[#F28C28]" />
                    <span>ELAPSED TIME</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setTimerRunning(!timerRunning)}
                      className="rounded p-1 text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/10"
                      title={timerRunning ? 'Pause' : 'Resume'}
                    >
                      {timerRunning ? <Pause size={13} /> : <Play size={13} />}
                    </button>
                    <button
                      onClick={() => setSeconds(0)}
                      className="rounded p-1 text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/10"
                      title="Reset Timer"
                    >
                      <RotateCcw size={13} />
                    </button>
                  </div>
                </div>
                <div className="font-mono text-3xl font-bold tracking-tight text-[#F4E6D3]">
                  {formatTime(seconds)}
                </div>
              </div>

              {/* Next Slide Preview */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-3.5 backdrop-blur-md">
                <div className="flex items-center justify-between text-xs text-[#888A90] font-mono mb-2">
                  <span>NEXT SLIDE ({idx + 2 <= totalSlides ? `${idx + 2}/${totalSlides}` : 'END'})</span>
                  <span className="text-[10px] text-[#888A90]">Auto-cued</span>
                </div>
                {nextSlide ? (
                  <div className="w-full opacity-75 hover:opacity-100 transition-opacity rounded-lg overflow-hidden border border-white/10 scale-95 origin-top">
                    <SlideView
                      slide={nextSlide}
                      themeId={currentThemeId}
                      designSystem={currentDesign}
                      first={false}
                    />
                  </div>
                ) : (
                  <div className="flex h-24 items-center justify-center rounded-lg border border-dashed border-white/10 text-xs text-[#888A90] font-mono">
                    End of presentation
                  </div>
                )}
              </div>

              {/* Speaker Notes */}
              <div className="flex flex-1 flex-col rounded-xl border border-white/[0.08] bg-white/[0.03] p-4 backdrop-blur-md overflow-hidden">
                <div className="flex items-center gap-1.5 text-xs text-[#888A90] font-mono mb-2.5">
                  <FileText size={14} className="text-[#F28C28]" />
                  <span>SPEAKER NOTES</span>
                </div>
                <div className="flex-1 overflow-y-auto pr-1 text-sm text-[#C5C0B8] leading-relaxed font-sans">
                  {currentSlide?.speaker_notes ? (
                    <p className="whitespace-pre-wrap">{currentSlide.speaker_notes}</p>
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-[#888A90] italic">
                      No speaker notes for this slide.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Floating Navigation Toolbar */}
      <footer className="flex h-16 items-center justify-between border-t border-white/[0.08] bg-[#101114]/90 px-8 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <button
            disabled={idx === 0}
            onClick={() => setIdx((i) => Math.max(0, i - 1))}
            className="liquid-glass-btn flex items-center gap-1 rounded-full px-3.5 py-1.5 text-xs font-medium text-[#F4E6D3] disabled:opacity-30 cursor-pointer transition-colors"
          >
            <ChevronLeft size={16} />
            <span>Previous</span>
          </button>
          <button
            disabled={idx === totalSlides - 1}
            onClick={() => setIdx((i) => Math.min(totalSlides - 1, i + 1))}
            className="liquid-glass-btn flex items-center gap-1 rounded-full px-3.5 py-1.5 text-xs font-medium text-[#F4E6D3] disabled:opacity-30 cursor-pointer transition-colors"
          >
            <span>Next</span>
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Slide Tracker Thumbnail Dots */}
        <div className="flex items-center gap-1.5 max-w-md overflow-x-auto py-1">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setIdx(i)}
              className={`h-2 rounded-full transition-all cursor-pointer ${
                i === idx
                  ? 'w-6 bg-[#F28C28]'
                  : 'w-2 bg-white/20 hover:bg-white/40'
              }`}
              title={`Slide ${i + 1}`}
            />
          ))}
        </div>

        <div className="flex items-center gap-3 text-xs text-zinc-500 font-mono">
          <span>Navigate: [←] [→] or [Space]</span>
          <span>•</span>
          <span>View: [T]</span>
          <span>•</span>
          <span>Exit: [Esc]</span>
        </div>
      </footer>
    </div>,
    document.body
  )
}

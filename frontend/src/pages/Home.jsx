import ModernTemplateCard from '../components/ModernTemplateCard'
import DropdownPopover from '../components/DropdownPopover'
import { useTypewriterPlaceholder } from '../hooks/useTypewriterPlaceholder'
import { useState, useRef } from 'react'
import { Check } from 'lucide-react'
import { DESIGN_SYSTEMS } from '../services/designSystems'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'

const SUGGESTIONS = [
  'Build a cinematic AI technology pitch deck.',
  'Create an editorial presentation about climate change.',
  'Turn my research paper into a visual presentation.',
  'Design a premium startup investor deck.',
]

export default function Home({ onNavigate, onStartWithPrompt, onOpenDocuments, onRequireLogin }) {
  const { toast, user } = useApp()
  const [prompt, setPrompt] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [deepResearch, setDeepResearch] = useState(true)
  const [selectedStyle, setSelectedStyle] = useState('linear_dark')
  const [styleMenuOpen, setStyleMenuOpen] = useState(false)
  const fileRef = useRef(null)
  const promptRef = useRef(null)
  const styleTriggerRef = useRef(null)

  const { placeholder, handleInteraction } = useTypewriterPlaceholder({
    defaultPlaceholder: 'What would you like to create today?',
  })

  const currentSystem = DESIGN_SYSTEMS.find((ds) => ds.id === selectedStyle) || DESIGN_SYSTEMS[0]

  const handleSelectSuggestion = (text) => {
    handleInteraction()
    setPrompt(text)
    promptRef.current?.focus()
  }

  const handleSubmit = () => {
    if (!prompt.trim()) return
    const cleanPrompt = prompt.trim()
    sessionStorage.setItem('initialPrompt', cleanPrompt)
    sessionStorage.setItem('initialStyle', selectedStyle)
    sessionStorage.setItem('initialDeepResearch', deepResearch ? '1' : '0')
    if (onStartWithPrompt) {
      onStartWithPrompt(cleanPrompt)
    } else {
      onNavigate?.('chat')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (e.metaKey || e.ctrlKey || !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    }
  }

  const handleFileUpload = async (files) => {
    if (!user) {
      onRequireLogin?.()
      toast('Sign in before uploading a document.', 'info')
      return
    }
    for (const f of files) {
      try {
        await api.upload(f)
        toast(`${f.name} uploaded successfully.`, 'success')
      } catch (e) {
        toast(`${f.name}: ${e.message}`, 'error')
      }
    }
  }

  const handleUseTemplate = (name, desc) => {
    const fullMessage = `Create a presentation in the ${name} style: ${desc}`
    sessionStorage.setItem('initialPrompt', fullMessage)
    if (onStartWithPrompt) {
      onStartWithPrompt(fullMessage)
    } else {
      onNavigate?.('chat')
    }
  }

  return (
    <div className="home-shell relative min-h-screen bg-[#101114] text-[#F4E6D3] font-body-md text-body-md antialiased overflow-x-hidden selection:bg-[#F28C28]/30 selection:text-[#F4E6D3]">
      {/* Hidden File Input */}
      <input
        ref={fileRef}
        type="file"
        multiple
        accept=".pdf,.docx,.pptx,.txt"
        hidden
        onChange={(e) => {
          handleFileUpload([...e.target.files])
          e.target.value = ''
        }}
      />

      {/* Ambient Under-Glow & Micro Dotted Canvas */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute -top-40 -left-40 w-[650px] h-[650px] bg-[#F28C28]/10 rounded-full blur-[180px]" />
        <div className="absolute -top-40 -right-40 w-[650px] h-[650px] bg-[#DFA36D]/08 rounded-full blur-[190px]" />
        <div className="absolute inset-0 grid-pattern opacity-60" />
      </div>

      {/* Main Viewport Canvas */}
      <main className="relative z-10 pt-24 sm:pt-28 pb-16 max-w-7xl mx-auto px-4 sm:px-6 md:px-12">
        {/* Hero Section */}
        <section className="home-hero text-center max-w-5xl mx-auto mb-6 sm:mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] backdrop-blur-md mb-2">
            <span className="material-symbols-outlined text-[#F28C28] text-sm" data-icon="auto_awesome">
              auto_awesome
            </span>
            <span className="font-label-sm text-[11px] uppercase tracking-widest text-[#C5C0B8] font-mono">
              AI presentation studio
            </span>
          </div>

          <h1 className="font-display-xl text-display-xl-mobile md:text-display-xl text-[#F4E6D3] font-normal tracking-tighter leading-[1.1]">
            Turn your ideas into<br />
            <span className="italic font-display-xl text-[#F28C28]">extraordinary</span> presentations.
          </h1>

          <p className="font-headline-sm text-sm sm:text-base text-[#C5C0B8] max-w-2xl mx-auto font-normal tracking-normal mt-2">
            Research deeply. Design intelligently. Present beautifully.
          </p>
        </section>

        {/* Central Prompt Composer */}
        <section className="max-w-4xl mx-auto mb-6 sm:mb-8">
          <div className="prompt-shell relative group rounded-2xl transition-all duration-300">
            <div className="p-3.5 sm:p-5 relative">
              <textarea
                ref={promptRef}
                value={prompt}
                onFocus={() => {
                  setIsFocused(true)
                  handleInteraction()
                }}
                onClick={handleInteraction}
                onBlur={() => setIsFocused(false)}
                onChange={(e) => {
                  handleInteraction()
                  setPrompt(e.target.value)
                }}
                onKeyDown={handleKeyDown}
                rows={2}
                id="prompt-input"
                placeholder={prompt ? '' : placeholder}
                className="w-full bg-transparent border-0 resize-none p-0 text-[#F4E6D3] placeholder:text-[#F4E6D3]/70 font-normal text-sm sm:text-base focus:ring-0 focus:outline-none tracking-tight leading-relaxed min-h-[48px] sm:min-h-[56px] relative z-10"
              />

              {/* Bottom Integrated Controls Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2.5 pt-3 mt-1.5 border-t border-white/[0.08]">
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Upload Document Action */}
                  <button
                    type="button"
                    onClick={() => {
                      if (!user) {
                        onRequireLogin?.()
                        return
                      }
                      fileRef.current?.click()
                    }}
                    className="liquid-glass-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-sm" data-icon="attach_file">
                      attach_file
                    </span>
                    <span>Upload Document</span>
                  </button>

                  {/* Deep Research Toggle */}
                  <button
                    type="button"
                    id="deep-research-btn"
                    onClick={() => setDeepResearch(!deepResearch)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all text-xs font-medium cursor-pointer ${
                      deepResearch
                        ? 'border border-[#F28C28]/40 bg-[#F28C28]/15 text-[#F4E6D3] shadow-[0_0_15px_rgba(242,140,40,0.2)]'
                        : 'liquid-glass-btn text-[#C5C0B8] hover:text-[#F4E6D3]'
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm" data-icon="cognition">
                      cognition
                    </span>
                    <span>Deep Research</span>
                    {deepResearch && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#F28C28] animate-pulse" />
                    )}
                  </button>

                  {/* Design Style Selector Dropdown Trigger */}
                  <div className="relative">
                    <button
                      ref={styleTriggerRef}
                      type="button"
                      onClick={() => setStyleMenuOpen(!styleMenuOpen)}
                      className="liquid-glass-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: currentSystem.accent }}
                      />
                      <span className="truncate max-w-[130px] sm:max-w-none">
                        Style: {currentSystem.name}
                      </span>
                      <span className="material-symbols-outlined text-xs" data-icon="expand_more">
                        expand_more
                      </span>
                    </button>

                    {/* Portal-based Floating Popover (auto opens up/down, never clipped) */}
                    <DropdownPopover
                      triggerRef={styleTriggerRef}
                      isOpen={styleMenuOpen}
                      onClose={() => setStyleMenuOpen(false)}
                      widthClass="w-80 sm:w-96"
                    >
                      {({ maxHeight }) => (
                        <>
                          <div className="px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-[#C5C0B8] border-b border-white/10 mb-1 flex items-center justify-between">
                            <span>Presentation Design System</span>
                            <span className="text-[#DFA36D] font-semibold">{DESIGN_SYSTEMS.length} Modern Styles</span>
                          </div>
                          <div
                            style={{ maxHeight: Math.max(160, maxHeight - 42) }}
                            className="overflow-y-auto space-y-1 pr-1 scrollbar-thin"
                          >
                            {DESIGN_SYSTEMS.map((ds) => {
                              const isSelected = selectedStyle === ds.id
                              return (
                                <button
                                  key={ds.id}
                                  type="button"
                                  onClick={() => {
                                    setSelectedStyle(ds.id)
                                    setStyleMenuOpen(false)
                                  }}
                                  className={`w-full text-left px-3 py-2 rounded-xl transition-all flex items-center justify-between group cursor-pointer ${
                                    isSelected
                                      ? 'bg-[#F28C28]/16 text-[#F4E6D3] font-semibold border border-[#F28C28]/35 shadow-sm'
                                      : 'text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.07]'
                                  }`}
                                >
                                  <div className="flex items-center gap-2.5 min-w-0">
                                    <span
                                      className="w-3.5 h-3.5 rounded-full shrink-0 border border-white/20"
                                      style={{ backgroundColor: ds.accent }}
                                    />
                                    <div className="min-w-0">
                                      <div className="text-xs sm:text-sm font-semibold text-[#F4E6D3] tracking-tight leading-tight truncate">
                                        {ds.name}
                                      </div>
                                      <div className="text-[10px] text-[#888A90] line-clamp-1 leading-tight mt-0.5">
                                        {ds.tagline}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-1.5 shrink-0 ml-2">
                                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-white/10 text-[#888A90] uppercase">
                                      {ds.category.split('&')[0].trim()}
                                    </span>
                                    {isSelected && <Check size={14} className="text-[#F28C28] shrink-0" />}
                                  </div>
                                </button>
                              )
                            })}
                          </div>
                        </>
                      )}
                    </DropdownPopover>
                  </div>
                </div>

                {/* Submit Generation Action */}
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!prompt.trim()}
                  aria-label="Send prompt"
                  className="w-9 h-9 sm:w-10 sm:h-10 rounded-full liquid-glass-btn-primary flex items-center justify-center transition-all duration-200 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
                >
                  <span className="material-symbols-outlined text-base sm:text-lg text-[#101114]" data-icon="arrow_upward">
                    arrow_upward
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* Prompt Suggestion Chips */}
          <div className="mt-4 sm:mt-5 flex flex-wrap items-center justify-center gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => handleSelectSuggestion(s)}
                className="liquid-glass-pill px-3.5 py-1.5 rounded-full text-[#C5C0B8] hover:text-[#DFA36D] transition-all duration-200 text-xs cursor-pointer"
              >
                “{s}”
              </button>
            ))}
          </div>
        </section>

        {/* Editorial Spacing */}
        <div className="h-6 sm:h-8" />

        {/* Template Discovery Section */}
        <section>
          {/* Section Header */}
          <div className="text-center max-w-2xl mx-auto mb-14 space-y-2">
            <h2 className="font-headline-md text-headline-md text-[#F4E6D3] font-normal tracking-tight">
              Explore creative directions
            </h2>
            <p className="font-body-md text-body-md text-[#888A90]">
              Curated architectural aesthetics for high-stakes narratives.
            </p>
          </div>

          {/* 6 Modern Aesthetic Direction Cards (1 col mobile, 2 col tablet, 3 col desktop) */}
          <div className="template-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
            {DESIGN_SYSTEMS.slice(0, 6).map((tmpl) => (
              <ModernTemplateCard
                key={tmpl.id}
                tmpl={tmpl}
                onInspect={() => onNavigate?.('templates')}
                onUse={() => handleUseTemplate(tmpl.name, tmpl.tagline)}
              />
            ))}
          </div>
        </section>
      </main>

      {/* Shared Component: Footer (Minimal Editorial) */}
      <footer className="border-t border-white/[0.08] bg-[#101114] text-[#888A90] py-8 z-20">
        <div className="flex flex-col md:flex-row justify-between items-center max-w-7xl mx-auto px-6 md:px-12 w-full gap-4">
          <div className="font-label-sm text-label-sm text-[#888A90] text-center md:text-left">
            © 2026 SlideMind AI Studio. Architectural presentation intelligence. Model v4.2.
          </div>
          <div className="flex items-center gap-6 font-label-sm text-label-sm text-[#888A90]">
            <a className="hover:text-[#F4E6D3] transition-colors duration-200" href="/privacy">
              Privacy Policy
            </a>
            <a className="hover:text-[#F4E6D3] transition-colors duration-200" href="/terms">
              Terms of Service
            </a>
            <span className="hover:text-[#F4E6D3] transition-colors duration-200 font-mono">
              Shortcuts [⌘K]
            </span>
            <a className="hover:text-[#F4E6D3] transition-colors duration-200" href="#">
              Documentation
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

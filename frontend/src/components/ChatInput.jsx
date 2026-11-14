import { useEffect, useRef, useState } from 'react'
import { Check } from 'lucide-react'
import { DESIGN_SYSTEMS } from '../services/designSystems'
import DropdownPopover from './DropdownPopover'
import { useTypewriterPlaceholder } from '../hooks/useTypewriterPlaceholder'

const ACCEPT = '.pdf,.docx,.pptx,.txt'

export default function ChatInput({
  onSend,
  onStop,
  busy = false,
  onFiles,
  disabled,
  onOpenTemplates,
  selectedTheme,
  onSelectTheme,
  inConversation = false,
}) {
  const [text, setText] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [deepResearch, setDeepResearch] = useState(true)
  const [density, setDensity] = useState('detailed') // 'detailed' | 'balanced' | 'concise'
  const [showStyleMenu, setShowStyleMenu] = useState(false)
  const [showDensityMenu, setShowDensityMenu] = useState(false)
  const [currentStyle, setCurrentStyle] = useState(selectedTheme || 'linear_dark')
  const fileRef = useRef(null)
  const areaRef = useRef(null)
  const styleTriggerRef = useRef(null)
  const densityTriggerRef = useRef(null)

  const { placeholder: typewriterPlaceholder, handleInteraction } = useTypewriterPlaceholder({
    defaultPlaceholder: 'What presentation would you like to create today?',
  })

  useEffect(() => {
    const el = areaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, inConversation ? 90 : 120) + 'px'
    }
  }, [text, inConversation])

  const submit = () => {
    if (!text.trim() || disabled) return
    handleInteraction()
    const themeObj = DESIGN_SYSTEMS.find((d) => d.id === currentStyle)
    const options = {
      style: themeObj?.name || currentStyle,
      deepResearch,
      density,
    }
    onSend(text.trim(), options)
    setText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (e.metaKey || e.ctrlKey) {
        e.preventDefault()
        submit()
      } else if (!e.shiftKey) {
        e.preventDefault()
        submit()
      }
    }
  }

  const currentThemeObj =
    DESIGN_SYSTEMS.find((d) => d.id === currentStyle) || DESIGN_SYSTEMS[0]

  return (
    <div className="w-full">
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPT}
        multiple
        hidden
        onChange={(e) => {
          onFiles([...e.target.files])
          e.target.value = ''
        }}
      />

      {/* Main Composer Box */}
      <div
        className={`prompt-shell relative group rounded-2xl transition-all duration-300 ${
          inConversation
            ? 'bg-zinc-950/90 border border-white/[0.14] shadow-[0_15px_40px_rgba(0,0,0,0.85)]'
            : ''
        }`}
      >
        <div className={inConversation ? 'p-2.5 sm:p-3' : 'p-3.5 sm:p-4.5 relative'}>
          <textarea
            ref={areaRef}
            rows={inConversation ? 1 : 2}
            value={text}
            onFocus={() => {
              setIsFocused(true)
              handleInteraction()
            }}
            onClick={handleInteraction}
            onBlur={() => setIsFocused(false)}
            onChange={(e) => {
              handleInteraction()
              setText(e.target.value)
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              inConversation
                ? 'Reply, ask for adjustments, or request new slides…'
                : text
                ? ''
                : typewriterPlaceholder
            }
            className="w-full bg-transparent border-0 resize-none p-0 text-[#F4E6D3] placeholder:text-[#F4E6D3]/70 text-sm sm:text-base focus:ring-0 focus:outline-none tracking-tight leading-snug relative z-10"
          />

          {/* Bottom Integrated Controls Bar */}
          <div
            className={`flex flex-wrap items-center justify-between gap-2 ${
              inConversation ? 'pt-2 mt-0.5' : 'pt-3 mt-1'
            }`}
          >
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
              {/* Upload Document Action */}
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="liquid-glass-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
              >
                <span className="material-symbols-outlined text-sm">attach_file</span>
                <span>Upload</span>
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
                <span className="material-symbols-outlined text-sm">cognition</span>
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
                  onClick={() => {
                    setShowStyleMenu(!showStyleMenu)
                    setShowDensityMenu(false)
                  }}
                  className="liquid-glass-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: currentThemeObj.accent }}
                  />
                  <span className="truncate max-w-[120px] sm:max-w-none">
                    Style: {currentThemeObj.name}
                  </span>
                  <span className="material-symbols-outlined text-xs">expand_more</span>
                </button>

                {/* Portal-based Floating Popover (auto opens up/down, never clipped by composer) */}
                <DropdownPopover
                  triggerRef={styleTriggerRef}
                  isOpen={showStyleMenu}
                  onClose={() => setShowStyleMenu(false)}
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
                          const isSelected = currentStyle === ds.id
                          return (
                            <button
                              key={ds.id}
                              type="button"
                              onClick={() => {
                                setCurrentStyle(ds.id)
                                if (onSelectTheme) onSelectTheme(ds.id)
                                setShowStyleMenu(false)
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

              {/* Density Dropdown Trigger */}
              <div className="relative">
                <button
                  ref={densityTriggerRef}
                  type="button"
                  onClick={() => {
                    setShowDensityMenu(!showDensityMenu)
                    setShowStyleMenu(false)
                  }}
                  className="liquid-glass-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
                >
                  <span className="material-symbols-outlined text-sm">density_medium</span>
                  <span className="capitalize">Density: {density}</span>
                  <span className="material-symbols-outlined text-xs">expand_more</span>
                </button>

                {/* Portal-based Floating Popover for Density */}
                <DropdownPopover
                  triggerRef={densityTriggerRef}
                  isOpen={showDensityMenu}
                  onClose={() => setShowDensityMenu(false)}
                  widthClass="w-72 sm:w-80"
                >
                  {({ maxHeight }) => (
                    <>
                      <div className="px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-zinc-400 border-b border-white/10 mb-1">
                        Information Density
                      </div>
                      <div
                        style={{ maxHeight: Math.max(140, maxHeight - 42) }}
                        className="overflow-y-auto space-y-1"
                      >
                        {[
                          { id: 'detailed', label: 'Detailed (Default)', hint: 'Deep analysis, full context & verified sources' },
                          { id: 'balanced', label: 'Balanced', hint: 'Strategic mix of cards, headlines & visual space' },
                          { id: 'concise', label: 'Concise', hint: 'High-impact executive numbers & minimal copy' },
                        ].map((dm) => {
                          const isSelected = density === dm.id
                          return (
                            <button
                              key={dm.id}
                              type="button"
                              onClick={() => {
                                setDensity(dm.id)
                                setShowDensityMenu(false)
                              }}
                              className={`w-full text-left px-3 py-2 rounded-xl transition-all flex items-center justify-between group cursor-pointer ${
                                isSelected
                                  ? 'bg-[#F28C28]/16 text-[#F4E6D3] font-semibold border border-[#F28C28]/35 shadow-sm'
                                  : 'text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.07]'
                              }`}
                            >
                              <div className="min-w-0">
                                <div className="text-xs sm:text-sm font-semibold text-[#F4E6D3] leading-tight">
                                  {dm.label}
                                </div>
                                <div className="text-[10px] text-[#888A90] line-clamp-1 leading-tight mt-0.5">
                                  {dm.hint}
                                </div>
                              </div>
                              {isSelected && <Check size={14} className="text-[#F28C28] shrink-0 ml-2" />}
                            </button>
                          )
                        })}
                      </div>
                    </>
                  )}
                </DropdownPopover>
              </div>
            </div>

            {/* Submit / Stop Generation Action */}
            {busy ? (
              <button
                type="button"
                onClick={onStop}
                title="Stop generation"
                aria-label="Stop generation"
                className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-[#F28C28]/15 hover:bg-[#F28C28]/25 border border-[#F28C28]/40 flex items-center justify-center transition-all duration-200 active:scale-95 cursor-pointer shrink-0 text-[#F28C28] shadow-[0_0_15px_rgba(242,140,40,0.15)] group"
              >
                <div className="w-2.5 h-2.5 bg-[#F28C28] rounded-xs group-hover:scale-110 transition-transform" />
              </button>
            ) : (
              <button
                type="button"
                onClick={submit}
                disabled={disabled || !text.trim()}
                aria-label="Send prompt"
                className="w-8 h-8 sm:w-9 sm:h-9 rounded-full liquid-glass-btn-primary flex items-center justify-center transition-all duration-200 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
              >
                {disabled && !text.trim() ? (
                  <span className="material-symbols-outlined text-base text-[#101114] opacity-50">arrow_upward</span>
                ) : disabled ? (
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#101114] border-t-transparent" />
                ) : (
                  <span className="material-symbols-outlined text-base text-[#101114]">arrow_upward</span>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import {
  Sparkles,
  Zap,
  ArrowRight,
  Eye,
  Type,
  X,
  Layers,
  ChevronLeft,
  ChevronRight,
  Check,
  Search,
} from 'lucide-react'
import { DESIGN_SYSTEMS, CATEGORIES } from '../services/designSystems'
import SlideView from '../components/SlideView'
import ModernTemplateCard from '../components/ModernTemplateCard'

export default function Templates({ onUseTemplate, onBack }) {
  const [selectedCat, setSelectedCat] = useState('All Templates')
  const [search, setSearch] = useState('')
  const [previewTemplate, setPreviewTemplate] = useState(null)
  const [previewSlideIdx, setPreviewSlideIdx] = useState(0)

  const filtered = DESIGN_SYSTEMS.filter((t) => {
    const matchesCat =
      selectedCat === 'All Templates' || t.category === selectedCat
    const matchesSearch =
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.tagline.toLowerCase().includes(search.toLowerCase()) ||
      t.category.toLowerCase().includes(search.toLowerCase()) ||
      t.features.some((f) => f.toLowerCase().includes(search.toLowerCase()))
    return matchesCat && matchesSearch
  })

  // Simulated slide deck for the interactive preview modal
  const getSimulatedSlides = (tmpl) => [
    {
      title: tmpl.sampleTitle,
      content: {
        layout: 'full_bleed_hero',
        purpose: tmpl.sampleSubtitle,
        bullets: [{ text: tmpl.sampleSubtitle, source_ids: [] }],
      },
    },
    {
      title: 'Architectural Hierarchy & Systems',
      content: {
        layout: 'cards_hierarchy',
        cards: tmpl.sampleKpis.map((k, i) => ({
          title: k.label,
          description: k.description,
          badge: `0${i + 1}`,
        })),
        bullets: tmpl.features.map((f) => ({ text: f, source_ids: [] })),
      },
    },
    {
      title: 'Verified Performance & Traction',
      content: {
        layout: 'stats_kpi',
        kpis: tmpl.sampleKpis,
        bullets: [{ text: tmpl.sampleStat, source_ids: [] }],
      },
    },
    {
      title: 'Strategic Takeaway & Horizon',
      content: {
        layout: 'quote_testimonial',
        quote: {
          text: `“Applying ${tmpl.name} design philosophy establishes immediate visual authority and narrative conviction.”`,
          author: 'SlideMind Creative Direction',
          role: tmpl.tagline,
        },
        bullets: [{ text: 'Final strategic alignment', source_ids: [] }],
      },
    },
  ]

  return (
    <div className="home-shell relative min-h-screen overflow-y-auto text-on-surface p-3 sm:p-6 md:p-8 pt-20 sm:pt-28 md:pt-36">
      <div className="mx-auto max-w-7xl">
        {/* Studio Header */}
        <div className="mb-6 sm:mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.1] bg-white/[0.04] px-3.5 py-1 text-xs font-medium text-[#F4E6D3] shadow-xs backdrop-blur-md">
              <Layers size={13} className="text-[#F28C28]" />
              <span>Modern Presentation Architecture</span>
            </div>
            <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-[#F4E6D3] md:text-3xl">
              Explore Aesthetic Directions
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-[#888A90]">
              Curated linear design systems, high-utility minimalism, and bold visual storytelling.
            </p>
          </div>

          {/* Quick Search */}
          <div className="w-full md:w-72">
            <div className="relative">
              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888A90]"
              />
              <input
                type="text"
                placeholder="Search systems (Linear, Keynote, Stripe...)"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-xl border border-white/[0.12] bg-white/[0.04] py-2 pl-9 pr-4 text-xs font-medium text-[#F4E6D3] placeholder:text-[#888A90] focus:border-[#F28C28] focus:outline-hidden backdrop-blur-md transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Category Pill Filters (Horizontally scrollable on mobile) */}
        <div className="mb-6 flex gap-2 overflow-x-auto pb-2 scrollbar-none sm:flex-wrap">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCat(cat)}
              className={`shrink-0 rounded-full px-3.5 sm:px-4 py-1.5 text-xs font-medium transition-all cursor-pointer ${
                selectedCat === cat
                  ? 'liquid-glass-pill-active'
                  : 'liquid-glass-pill text-[#C5C0B8] hover:text-[#DFA36D]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Templates Grid (1 col on mobile, 2 on tablet, 3 on desktop) */}
        <div className="template-grid grid grid-cols-1 gap-5 sm:gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tmpl) => (
            <ModernTemplateCard
              key={tmpl.id}
              tmpl={tmpl}
              onInspect={(t) => {
                setPreviewTemplate(t)
                setPreviewSlideIdx(0)
              }}
              onUse={(t) => onUseTemplate(t)}
            />
          ))}
        </div>
      </div>

            {/* ========================================================= */}
      {/* EXPANDED INTERACTIVE MULTI-SLIDE PREVIEW MODAL             */}
      {/* ========================================================= */}
      {previewTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-2 sm:p-4 backdrop-blur-md">
          <div className="relative flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden liquid-glass-modal shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/[0.08] px-4 sm:px-6 py-3 sm:py-4">
              <div className="flex items-center gap-2.5">
                <div
                  className="h-3.5 w-3.5 rounded-full border border-white/20"
                  style={{ backgroundColor: previewTemplate.accent }}
                />
                <div>
                  <h2 className="text-sm sm:text-base font-bold text-[#F4E6D3]">
                    {previewTemplate.name} Design System
                  </h2>
                  <p className="text-[11px] text-[#DFA36D]">
                    {previewTemplate.fonts} · {previewTemplate.category}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setPreviewTemplate(null)}
                className="rounded-lg p-1.5 text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.08] cursor-pointer transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body: Active Slide View */}
            <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto p-3 sm:p-6">
              <div className="w-full max-w-3xl">
                {/* Slide Stage */}
                <div className="rounded-xl overflow-hidden shadow-2xl border border-white/[0.1]">
                  <SlideView
                    slide={getSimulatedSlides(previewTemplate)[previewSlideIdx]}
                    themeId={previewTemplate.id}
                    first={previewSlideIdx === 0}
                  />
                </div>

                {/* Slide Stepper Controls */}
                <div className="mt-3 sm:mt-4 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <button
                      disabled={previewSlideIdx === 0}
                      onClick={() => setPreviewSlideIdx((i) => Math.max(0, i - 1))}
                      className="liquid-glass-btn rounded-lg p-1.5 text-[#F4E6D3] disabled:opacity-30 cursor-pointer"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <span className="text-xs font-medium text-[#C5C0B8]">
                      Slide {previewSlideIdx + 1} of 4:
                      <span className="ml-1 text-[#F4E6D3] font-semibold">
                        {previewSlideIdx === 0
                          ? 'Hero Cover'
                          : previewSlideIdx === 1
                          ? 'Structured Cards'
                          : previewSlideIdx === 2
                          ? 'Metrics & Data'
                          : 'Conclusion & Quote'}
                      </span>
                    </span>
                    <button
                      disabled={previewSlideIdx === 3}
                      onClick={() => setPreviewSlideIdx((i) => Math.min(3, i + 1))}
                      className="liquid-glass-btn rounded-lg p-1.5 text-[#F4E6D3] disabled:opacity-30 cursor-pointer"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>

                  {/* Slide Thumbnail Dots */}
                  <div className="flex items-center gap-1.5">
                    {[0, 1, 2, 3].map((idx) => (
                      <button
                        key={idx}
                        onClick={() => setPreviewSlideIdx(idx)}
                        className={`h-2 rounded-full transition-all cursor-pointer ${
                          previewSlideIdx === idx
                            ? 'w-5 bg-[#F28C28]'
                            : 'w-2 bg-white/20 hover:bg-white/40'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-white/[0.08] bg-black/30 px-4 sm:px-6 py-3">
              <p className="hidden sm:block max-w-md text-xs text-[#888A90] truncate">
                {previewTemplate.tagline}
              </p>
              <div className="flex w-full sm:w-auto justify-end gap-2">
                <button
                  onClick={() => setPreviewTemplate(null)}
                  className="liquid-glass-btn rounded-full px-4 py-1.5 text-xs font-medium text-[#F4E6D3] cursor-pointer"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    const t = previewTemplate
                    setPreviewTemplate(null)
                    onUseTemplate(t)
                  }}
                  className="liquid-glass-btn-primary flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold cursor-pointer"
                >
                  <Zap size={13} className="text-[#101114]" /> <span>Create Deck With This System</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

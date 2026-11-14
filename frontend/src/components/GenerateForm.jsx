import { useEffect, useState } from 'react'
import { Loader2, Sparkles, Layers, ArrowRight } from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'
import { DESIGN_SYSTEMS, getDesignSystemById } from '../services/designSystems'

const AUDIENCES = [
  ['business_executives', 'Business Executives'],
  ['technical_professionals', 'Technical Professionals'],
  ['college_students', 'College Students'],
  ['researchers', 'Researchers & Scientists'],
  ['school_students', 'School Students'],
  ['beginners', 'General Audience / Beginners'],
]
const label = (s) => s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
const field =
  'w-full rounded-xl border border-white/[0.14] bg-[#1E2026] px-3.5 py-2 text-xs text-[#F4E6D3] outline-none focus:border-[#F28C28] transition-colors placeholder:text-[#888A90]'

export default function GenerateForm({ onStarted, onCancel, initialTheme, initialTopic }) {
  const { user, toast, preferences } = useApp()
  const [docs, setDocs] = useState([])
  const [busy, setBusy] = useState(false)
  const [f, setF] = useState({
    topic: initialTopic || '',
    slide_count: preferences?.defaultSlideCount || 10,
    audience: 'business_executives',
    language: 'English',
    duration_minutes: '',
    citation_style: 'APA',
    complexity: 'intermediate',
    theme: initialTheme || getDesignSystemById(preferences?.defaultDesignSystem || 'swiss_bauhaus')?.id || 'swiss_bauhaus',
    use_web_research: false,
    publish: false,
    document_ids: [],
  })

  useEffect(() => {
    if (initialTheme) set('theme', initialTheme)
    if (initialTopic) set('topic', initialTopic)
  }, [initialTheme, initialTopic])

  useEffect(() => {
    api.documents().then(setDocs).catch(() => {})
  }, [])
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }))
  const toggleDoc = (id) =>
    set(
      'document_ids',
      f.document_ids.includes(id)
        ? f.document_ids.filter((d) => d !== id)
        : [...f.document_ids, id]
    )

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const body = {
        ...f,
        slide_count: Number(f.slide_count),
        duration_minutes: f.duration_minutes ? Number(f.duration_minutes) : undefined,
      }
      if (body.duration_minutes === undefined) delete body.duration_minutes
      onStarted(await api.createPresentation(body))
    } catch (err) {
      toast(err.message, 'error')
      if (err.code === 'job_in_progress' && err.details?.job_id) {
        onStarted({ job_id: err.details.job_id })
      }
    } finally {
      setBusy(false)
    }
  }

  const L = ({ children, text }) => (
    <label className="block text-xs font-medium">
      <span className="mb-1.5 block text-[#C5C0B8]">{text}</span>
      {children}
    </label>
  )

  return (
    <div className="min-h-full overflow-y-auto p-4 md:p-8">
      <form
        onSubmit={submit}
        className="mx-auto w-full max-w-2xl liquid-glass-card p-6 space-y-4"
      >
        <div className="border-b border-white/[0.08] pb-4">
          <h2 className="text-lg font-bold text-[#F4E6D3]">Create New Presentation</h2>
          <p className="text-xs text-[#888A90]">
            Define topic, audience, and design system for multi-slide generation
          </p>
        </div>

        <L text="Presentation Topic & Objectives">
          <textarea
            required
            minLength={3}
            maxLength={500}
            rows={3}
            value={f.topic}
            onChange={(e) => set('topic', e.target.value)}
            className={field}
            placeholder="e.g. Q4 Executive Strategy: AI Infrastructure Scaling, Cost Optimization, and Team Growth"
          />
        </L>

        <div className="grid gap-3 sm:grid-cols-2">
          <L text="Target Audience">
            <select
              value={f.audience}
              onChange={(e) => set('audience', e.target.value)}
              className={field}
            >
              {AUDIENCES.map(([v, l]) => (
                <option key={v} value={v} className="bg-[#1E2026] text-[#F4E6D3]">
                  {l}
                </option>
              ))}
            </select>
          </L>

          <L text="Slide Count (3–40)">
            <input
              type="number"
              min={3}
              max={40}
              value={f.slide_count}
              onChange={(e) => set('slide_count', e.target.value)}
              className={field}
            />
          </L>

          <L text="Presentation Language">
            <input
              value={f.language}
              maxLength={40}
              onChange={(e) => set('language', e.target.value)}
              className={field}
            />
          </L>

          <L text="Duration in Minutes (optional)">
            <input
              type="number"
              min={1}
              max={180}
              value={f.duration_minutes}
              onChange={(e) => set('duration_minutes', e.target.value)}
              className={field}
              placeholder="e.g. 15"
            />
          </L>

          <L text="Content Depth">
            <select
              value={f.complexity}
              onChange={(e) => set('complexity', e.target.value)}
              className={field}
            >
              {['basic', 'intermediate', 'advanced'].map((v) => (
                <option key={v} value={v} className="bg-[#1E2026] text-[#F4E6D3]">
                  {label(v)}
                </option>
              ))}
            </select>
          </L>

          <L text="Citation Format">
            <select
              value={f.citation_style}
              onChange={(e) => set('citation_style', e.target.value)}
              className={field}
            >
              {['APA', 'MLA', 'IEEE', 'none'].map((v) => (
                <option key={v} value={v} className="bg-[#1E2026] text-[#F4E6D3]">
                  {v}
                </option>
              ))}
            </select>
          </L>

          <div className="sm:col-span-2">
            <L text="Design System (15 Authentic Systems)">
              <select
                value={f.theme}
                onChange={(e) => set('theme', e.target.value)}
                className={field}
              >
                {DESIGN_SYSTEMS.map((ds) => (
                  <option key={ds.id} value={ds.id} className="bg-[#1E2026] text-[#F4E6D3]">
                    {ds.name} — {ds.category} ({ds.tagline})
                  </option>
                ))}
              </select>
            </L>
          </div>
        </div>

        {/* Documents */}
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
          <div className="text-xs font-semibold text-[#F4E6D3] mb-1.5">
            Document Grounding
          </div>
          {docs.length === 0 ? (
            <p className="text-xs text-[#888A90]">
              No uploaded documents. Upload documents from the sidebar to enable RAG citation grounding.
            </p>
          ) : (
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {docs.map((d) => (
                <label
                  key={d.id}
                  className="flex items-center gap-2 text-xs text-[#C5C0B8] cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={f.document_ids.includes(d.id)}
                    onChange={() => toggleDoc(d.id)}
                    className="rounded border-white/20 bg-white/5 text-[#F28C28] focus:ring-[#F28C28]"
                  />
                  <span>{d.filename}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2 pt-1">
          <label className="flex items-center gap-2 text-xs text-[#C5C0B8] cursor-pointer">
            <input
              type="checkbox"
              checked={f.use_web_research}
              onChange={(e) => set('use_web_research', e.target.checked)}
              className="rounded border-white/20 bg-white/5 text-[#F28C28] focus:ring-[#F28C28]"
            />
            <span>Enable deep web research and factual citation retrieval</span>
          </label>

          <label className="flex items-start gap-2 text-xs text-[#C5C0B8] cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5 rounded border-white/20 bg-white/5 text-[#F28C28] focus:ring-[#F28C28]"
              disabled={!user?.google_connected}
              checked={f.publish}
              onChange={(e) => set('publish', e.target.checked)}
            />
            <span>
              Publish directly to Google Slides upon generation
              {!user?.google_connected && (
                <span className="block text-[11px] text-[#888A90]">
                  Connect Google Slides in the sidebar or settings to enable automatic publishing.
                </span>
              )}
            </span>
          </label>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.08]">
          <button
            type="button"
            onClick={onCancel}
            className="liquid-glass-btn rounded-full px-4 py-2 text-xs font-medium text-[#C5C0B8] cursor-pointer"
          >
            Cancel
          </button>
          <button
            disabled={busy}
            className="liquid-glass-btn-primary flex items-center gap-2 rounded-full px-5 py-2 text-xs font-semibold text-[#101114] cursor-pointer"
          >
            {busy ? <Loader2 size={15} className="animate-spin text-[#101114]" /> : <Sparkles size={15} />}
            <span>Generate Presentation</span>
          </button>
        </div>
      </form>
    </div>
  )
}

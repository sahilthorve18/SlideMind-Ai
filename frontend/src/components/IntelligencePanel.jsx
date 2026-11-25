import { useEffect, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  Award,
  CheckCircle2,
  Clock,
  Info,
  Loader2,
  RefreshCw,
  Sparkles,
  Wand2,
  Zap,
} from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'

const gradeColors = {
  'A+': 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20 dark:text-emerald-400',
  A: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20 dark:text-emerald-400',
  B: 'bg-blue-500/10 text-blue-600 border-blue-500/20 dark:text-blue-400',
  C: 'bg-amber-500/10 text-amber-600 border-amber-500/20 dark:text-amber-400',
  D: 'bg-orange-500/10 text-orange-600 border-orange-500/20 dark:text-orange-400',
  F: 'bg-rose-500/10 text-rose-600 border-rose-500/20 dark:text-rose-400',
}

const statusColors = {
  optimal: 'bg-emerald-500',
  balanced: 'bg-emerald-500',
  detailed: 'bg-blue-500',
  brisk: 'bg-cyan-500',
  rushed: 'bg-amber-500',
  drag: 'bg-rose-500',
}

export default function IntelligencePanel({ presentationId, onSelectSlide, onReloadPresentation }) {
  const { toast } = useApp()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [fixing, setFixing] = useState('')

  const fetchIntelligence = async () => {
    setLoading(true)
    try {
      const res = await api.getIntelligence(presentationId)
      setData(res)
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (presentationId) fetchIntelligence()
  }, [presentationId])

  const runFix = async (actionType, slidePos = null) => {
    setFixing(actionType)
    try {
      const res = await api.fixIntelligence(presentationId, actionType, slidePos)
      setData(res.intelligence)
      if (onReloadPresentation) await onReloadPresentation()
      toast(`Applied ${actionType.replace(/_/g, ' ')} (${res.fix_result.modified_slides} slides updated).`, 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setFixing('')
    }
  }

  if (loading && !data) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-sm text-slate-500">
        <Loader2 className="animate-spin text-brand-500" size={24} />
        <p>Analyzing presentation intelligence...</p>
      </div>
    )
  }

  if (!data) return null

  const { overall_score, grade, summary, categories = {}, issues = [], recommendations = [], pacing_timeline = [], visual_critique = null } = data

  const filteredIssues = issues.filter((iss) => {
    if (filter === 'all') return true
    if (filter === 'critical') return iss.severity === 'critical'
    if (filter === 'warning') return iss.severity === 'warning'
    return iss.dimension === filter
  })

  return (
    <div className="space-y-6">
      {/* Header Health Score */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-5 dark:border-slate-800 dark:from-slate-900 dark:to-slate-950">
        <div className="flex items-center gap-4">
          <div
            className={`flex h-16 w-16 items-center justify-center rounded-2xl border text-2xl font-bold shadow-sm ${gradeColors[grade] || gradeColors.B}`}
          >
            {grade}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold">Presentation Health Score</h2>
              <span className="rounded-full bg-brand-500/10 px-2 py-0.5 text-xs font-semibold text-brand-600 dark:text-brand-400">
                {overall_score}/100
              </span>
            </div>
            <p className="mt-0.5 max-w-xl text-xs text-slate-600 dark:text-slate-400">{summary}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchIntelligence}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* 6 Core Pillars Breakdown */}
      <div>
        <div className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Quality Dimensions</div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(categories).map(([key, cat]) => {
            const pct = cat.score ?? 0
            const barColor = pct >= 85 ? 'bg-emerald-500' : pct >= 70 ? 'bg-blue-500' : pct >= 50 ? 'bg-amber-500' : 'bg-rose-500'
            return (
              <div
                key={key}
                className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="flex items-center justify-between text-xs font-medium">
                  <span className="text-slate-700 dark:text-slate-300">{cat.label}</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">{pct}%</span>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                  <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${pct}%` }} />
                </div>
                <div className="mt-2.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                  {key === 'clarity' && (
                    <>
                      <span>{cat.metrics.avg_bullets_per_slide} bullets/slide</span>
                      <span>{cat.metrics.avg_words_per_bullet} words/bullet</span>
                    </>
                  )}
                  {key === 'structure' && (
                    <>
                      <span>{cat.metrics.total_slides} slides</span>
                      <span>{cat.metrics.has_conclusion ? 'Has wrap-up' : 'No conclusion'}</span>
                    </>
                  )}
                  {key === 'pacing' && (
                    <>
                      <span>~{cat.metrics.estimated_total_minutes} min total</span>
                      <span>{cat.metrics.slides_with_notes}/{cat.metrics.total_slides} notes</span>
                    </>
                  )}
                  {key === 'sourcing' && (
                    <>
                      <span>{cat.metrics.citation_coverage_pct}% sourced</span>
                      <span>{cat.metrics.unique_sources_cited} sources</span>
                    </>
                  )}
                  {key === 'audience' && (
                    <>
                      <span className="capitalize">{cat.metrics.target_audience?.replace('_', ' ')}</span>
                      <span>{cat.metrics.matched_key_terms} key signals</span>
                    </>
                  )}
                  {key === 'visual_variety' && (
                    <>
                      <span>{cat.metrics.unique_layouts} layout types</span>
                      <span>{Math.round(cat.metrics.visual_ratio * 100)}% visual</span>
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Vision Render Audit */}
      {visual_critique && visual_critique.evaluated_slides > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Award size={16} className="text-brand-500" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Vision Render Audit
              </h3>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {visual_critique.average_score !== null && (
                <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 font-semibold text-emerald-600 dark:text-emerald-400">
                  Avg {visual_critique.average_score}/100
                </span>
              )}
              <span className="text-slate-500">
                {visual_critique.passed_slides}/{visual_critique.evaluated_slides} slides passed
              </span>
              {visual_critique.repaired_slides?.length > 0 && (
                <span className="rounded-full bg-brand-500/10 px-2 py-0.5 text-[11px] font-medium text-brand-600 dark:text-brand-400">
                  Auto-repaired: {visual_critique.repaired_slides.map((n) => `S${n}`).join(', ')}
                </span>
              )}
            </div>
          </div>
          {visual_critique.slides?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {visual_critique.slides.map((s) => (
                <button
                  key={s.slide_number}
                  onClick={() => onSelectSlide(s.slide_number - 1)}
                  className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition hover:border-brand-500 ${
                    s.status === 'error' || s.status === 'skipped'
                      ? 'border-slate-200 text-slate-500 dark:border-slate-700'
                      : s.passed
                      ? 'border-emerald-500/30 bg-emerald-50/40 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-300'
                      : 'border-amber-500/30 bg-amber-50/40 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300'
                  }`}
                >
                  S{s.slide_number}: {s.score !== null ? `${s.score}/100` : s.status}
                  {s.repaired ? ' (repaired)' : ''}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pacing Timeline */}
      {pacing_timeline.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-brand-500" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Pacing & Speaking Time Timeline
              </h3>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-500">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500" /> Balanced (45–90s)
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-blue-500" /> Detailed (90–150s)
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-rose-500" /> Drag (&gt;150s)
              </span>
            </div>
          </div>

          <div className="flex items-end gap-1.5 overflow-x-auto pb-2 pt-4">
            {pacing_timeline.map((item) => {
              const maxSec = Math.max(...pacing_timeline.map((t) => t.seconds), 120)
              const heightPct = Math.max(20, Math.min(100, (item.seconds / maxSec) * 100))
              const color = statusColors[item.status] || 'bg-brand-500'

              return (
                <button
                  key={item.slide_position}
                  onClick={() => onSelectSlide(item.slide_position - 1)}
                  className="group flex flex-1 min-w-[48px] flex-col items-center gap-1 text-center"
                >
                  <span className="text-[10px] font-medium text-slate-500 group-hover:text-brand-500">
                    {item.formatted_time}
                  </span>
                  <div className="flex h-24 w-full items-end justify-center rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
                    <div
                      className={`w-full rounded transition-all group-hover:brightness-110 ${color}`}
                      style={{ height: `${heightPct}%` }}
                    />
                  </div>
                  <span className="truncate text-[10px] font-semibold text-slate-700 dark:text-slate-300">
                    S{item.slide_position}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Quick Fixes Toolbar */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-brand-500/20 bg-brand-50/50 p-3 text-xs dark:bg-brand-950/20">
        <Sparkles size={16} className="text-brand-500 shrink-0" />
        <span className="font-semibold text-slate-700 dark:text-slate-200">AI Auto-Fixes:</span>
        <button
          onClick={() => runFix('generate_missing_notes')}
          disabled={Boolean(fixing)}
          className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 font-medium hover:border-brand-500 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
        >
          {fixing === 'generate_missing_notes' ? <Loader2 size={12} className="animate-spin" /> : <Wand2 size={12} />}
          Generate Missing Notes
        </button>
        <button
          onClick={() => runFix('trim_overflow')}
          disabled={Boolean(fixing)}
          className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 font-medium hover:border-brand-500 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
        >
          {fixing === 'trim_overflow' ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
          Trim Text Overflow
        </button>
        <button
          onClick={() => runFix('auto_balance')}
          disabled={Boolean(fixing)}
          className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 font-medium hover:border-brand-500 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
        >
          {fixing === 'auto_balance' ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
          Auto-Balance Deck
        </button>
      </div>

      {/* Issues & Recommendations */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Diagnostics & Actionable Recommendations ({filteredIssues.length})
          </div>
          <div className="flex gap-1 overflow-x-auto text-xs">
            {['all', 'critical', 'warning', 'clarity', 'pacing', 'sourcing', 'structure'].map((t) => (
              <button
                key={t}
                onClick={() => setFilter(t)}
                className={`rounded-lg px-2.5 py-1 capitalize transition ${
                  filter === t
                    ? 'bg-brand-500 font-semibold text-white'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {filteredIssues.length === 0 ? (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-50/50 p-4 text-xs text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300">
            <CheckCircle2 size={16} className="text-emerald-500" />
            <span>No issues found in this category. Your deck meets quality standards!</span>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredIssues.map((iss, i) => {
              const isCrit = iss.severity === 'critical'
              const isWarn = iss.severity === 'warning'
              return (
                <div
                  key={i}
                  className={`flex items-start gap-3 rounded-xl border p-3.5 transition hover:shadow-sm ${
                    isCrit
                      ? 'border-rose-200 bg-rose-50/40 dark:border-rose-900/50 dark:bg-rose-950/20'
                      : isWarn
                      ? 'border-amber-200 bg-amber-50/40 dark:border-amber-900/50 dark:bg-amber-950/20'
                      : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900'
                  }`}
                >
                  {isCrit ? (
                    <AlertCircle size={16} className="mt-0.5 shrink-0 text-rose-500" />
                  ) : isWarn ? (
                    <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-500" />
                  ) : (
                    <Info size={16} className="mt-0.5 shrink-0 text-blue-500" />
                  )}

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                        {iss.message}
                      </span>
                      {iss.slide && (
                        <button
                          onClick={() => onSelectSlide(iss.slide - 1)}
                          className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-bold text-slate-700 hover:bg-brand-500 hover:text-white dark:bg-slate-800 dark:text-slate-300"
                        >
                          Jump to Slide {iss.slide}
                        </button>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                      💡 <b>Suggestion:</b> {iss.suggestion}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

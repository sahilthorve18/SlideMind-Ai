import { useLayoutEffect, useRef, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  Layers,
  Terminal,
  Compass,
} from 'lucide-react'
import { getDesignSystemById } from '../services/designSystems'
import { renderAdvancedLayout } from './SlideCanvas/LayoutDispatcher'
import SceneView from './SceneView'

const W = 960,
  H = 540
const PALETTE = [
  '#6366f1',
  '#22c55e',
  '#f59e0b',
  '#ef4444',
  '#06b6d4',
  '#0284c7',
  '#84cc16',
  '#f97316',
]
const rgb = (t) =>
  Array.isArray(t)
    ? `rgb(${t.map((v) => Math.round(v * 255)).join(',')})`
    : t || '#ffffff'

function Chart({ chart, color }) {
  const data = (chart.labels || []).map((l, i) => ({
    name: l,
    value: (chart.values || [])[i] || 0,
  }))
  const axis = { stroke: color, fontSize: 13 }
  return (
    <div style={{ width: '100%', height: 260 }}>
      <ResponsiveContainer>
        {chart.type === 'pie' ? (
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              label
              outerRadius={95}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        ) : chart.type === 'line' ? (
          <LineChart data={data}>
            <CartesianGrid strokeOpacity={0.15} />
            <XAxis dataKey="name" {...axis} />
            <YAxis {...axis} />
            <Tooltip />
            <Line
              dataKey="value"
              stroke={PALETTE[0]}
              strokeWidth={3}
              dot={{ r: 5 }}
            />
          </LineChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeOpacity={0.15} />
            <XAxis dataKey="name" {...axis} />
            <YAxis {...axis} />
            <Tooltip />
            <Bar dataKey="value" fill={PALETTE[0]} radius={[6, 6, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

function Diagram({ diagram, color }) {
  const nodes = diagram.nodes || []
  const cols = Math.min(4, Math.max(1, nodes.length)),
    rows = Math.ceil(nodes.length / cols)
  const cw = 760 / cols,
    ch = 250 / rows
  const pos = Object.fromEntries(
    nodes.map((n, i) => [
      n.id,
      {
        x: 100 + (i % cols) * cw + cw / 2 - 50,
        y: Math.floor(i / cols) * ch + ch / 2 + 10,
      },
    ])
  )
  return (
    <svg viewBox="0 0 960 270" width="100%" height={260}>
      <defs>
        <marker
          id="arr"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M0 0L10 5L0 10z" fill={color} />
        </marker>
      </defs>
      {(diagram.edges || []).map(
        (e, i) =>
          pos[e.from] &&
          pos[e.to] && (
            <line
              key={i}
              x1={pos[e.from].x + 50}
              y1={pos[e.from].y}
              x2={pos[e.to].x + 50}
              y2={pos[e.to].y}
              stroke={color}
              strokeWidth="2"
              markerEnd="url(#arr)"
              opacity="0.6"
            />
          )
      )}
      {nodes.map((n) => (
        <g key={n.id}>
          <rect
            x={pos[n.id].x - 60}
            y={pos[n.id].y - 24}
            width="220"
            height="52"
            rx="8"
            fill={PALETTE[0]}
            opacity="0.9"
          />
          <text
            x={pos[n.id].x + 50}
            y={pos[n.id].y + 6}
            textAnchor="middle"
            fill="#fff"
            fontSize="15"
            fontWeight="bold"
          >
            {String(n.label).slice(0, 24)}
          </text>
        </g>
      ))}
    </svg>
  )
}

/**
 * SlideMind Studio Presentation Canvas.
 * Renders 15 authentically distinct design systems at native 960x540 16:9 widescreen.
 */
export default function SlideView({ slide, theme, themeId, designSystem, first }) {
  const wrap = useRef(null)
  const [scale, setScale] = useState(0.3)

  useLayoutEffect(() => {
    const el = wrap.current
    if (!el) return
    const ro = new ResizeObserver(() => setScale(el.clientWidth / W))
    ro.observe(el)
    setScale(el.clientWidth / W)
    return () => ro.disconnect()
  }, [])

  // Resolve authentic design system metadata
  const ds = (typeof designSystem === 'object' && designSystem !== null)
    ? designSystem
    : getDesignSystemById(themeId || (theme && theme.id) || (typeof designSystem === 'string' ? designSystem : null) || 'swiss_minimal')
  const style = ds.layout_style || 'swiss'

  // Colors & tokens
  const bgColor = ds.bg || (theme ? rgb(theme.background) : '#fbfbfa')
  const titleColor = ds.primary || (theme ? rgb(theme.title) : '#0a0a0c')
  const bodyColor = ds.secondary || (theme ? rgb(theme.body) : '#333338')
  const accentColor = ds.accent || '#eb3324'
  const cardBg = ds.cardBg || '#ffffff'
  const borderCol = ds.border || '#dcdcd8'
  const fontFam = ds.fonts || (theme?.font || 'Inter') + ', sans-serif'
  const radius = ds.cardRadius !== undefined ? ds.cardRadius : 12

  // Composed slides come with a solved layout scene (same one the PPTX/PDF are drawn from)
  if (slide?.scene) {
    return (
      <div ref={wrap} style={{ width: '100%', aspectRatio: '16 / 9', overflow: 'hidden', position: 'relative', borderRadius: 12,
        boxShadow: '0 8px 30px rgba(0,0,0,0.08)', backgroundColor: `#${slide.scene.bg}` }}>
        <div style={{ width: W, height: H, transform: `scale(${scale})`, transformOrigin: 'top left' }}>
          <SceneView key={slide.position + ':' + (slide.title || '')} scene={slide.scene} />
        </div>
      </div>
    )
  }

  const c = slide?.content || {}
  const bullets = c.bullets || []
  const layout = c.layout || (first ? 'full_bleed_hero' : 'cards_hierarchy')

  return (
    <div
      ref={wrap}
      style={{
        width: '100%',
        aspectRatio: '16 / 9',
        overflow: 'hidden',
        position: 'relative',
        borderRadius: 12,
        boxShadow: '0 8px 30px rgba(0,0,0,0.08)',
        backgroundColor: bgColor,
      }}
    >
      <div
        style={{
          width: W,
          height: H,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
          background: bgColor,
          fontFamily: fontFam,
          padding: '44px 56px',
          boxSizing: 'border-box',
          position: 'relative',
          color: bodyColor,
        }}
      >
        {/* ========================================================= */}
        {/* COVER / HERO SLIDE (First Slide or full_bleed_hero)      */}
        {/* ========================================================= */}
        {(layout === 'full_bleed_hero' || first) && (
          <div
            style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              position: 'relative',
              zIndex: 1,
            }}
          >
            {/* Optional High-Res Hero Photographic Backdrop */}
            {c.image?.url && (
              <div
                style={{
                  position: 'absolute',
                  inset: '-44px -56px',
                  zIndex: 0,
                  overflow: 'hidden',
                  pointerEvents: 'none',
                }}
              >
                <img
                  src={c.image.url}
                  alt={c.image.alt || slide?.title}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                  }}
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    background: ds.isDark
                      ? 'linear-gradient(90deg, rgba(8,10,14,0.92) 0%, rgba(8,10,14,0.76) 55%, rgba(8,10,14,0.3) 100%)'
                      : 'linear-gradient(90deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.8) 55%, rgba(255,255,255,0.3) 100%)',
                  }}
                />
              </div>
            )}
            <div style={{ position: 'relative', zIndex: 2 }}>
            {/* Style 1: Swiss International Cover */}
            {style === 'swiss' && (
              <div>
                <div style={{ width: 120, height: 4, background: accentColor, marginBottom: 28 }} />
                <div style={{ fontSize: 50, fontWeight: 900, color: titleColor, lineHeight: 1.1, letterSpacing: '-0.03em', maxWidth: 840 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 20, color: bodyColor, marginTop: 22, maxWidth: 760, lineHeight: 1.45 }}>
                  {c.purpose || bullets[0]?.text || 'Objective visual clarity and typographic precision'}
                </div>
                <div style={{ marginTop: 44, display: 'flex', alignItems: 'center', gap: 24, borderTop: `1px solid ${borderCol}`, paddingTop: 16 }}>
                  <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.12em', color: accentColor, textTransform: 'uppercase' }}>
                    INTERNATIONAL SYSTEM • 01
                  </span>
                  <span style={{ fontSize: 11, color: ds.muted }}>CONFIDENTIAL & PROPRIETARY</span>
                </div>
              </div>
            )}

            {/* Style 2: Brutalist Cover */}
            {style === 'brutalist' && (
              <div style={{ border: `3px solid ${titleColor}`, padding: 36, background: cardBg }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: `2px solid ${titleColor}`, paddingBottom: 12, marginBottom: 20 }}>
                  <span style={{ fontFamily: 'monospace', fontWeight: 900, fontSize: 12, background: accentColor, padding: '2px 8px' }}>
                    // REF: SPEC_2026
                  </span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 12 }}>DECK_POSITION_01</span>
                </div>
                <div style={{ fontSize: 48, fontWeight: 900, color: titleColor, textTransform: 'uppercase', lineHeight: 1.05, letterSpacing: '-0.02em' }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 16, fontFamily: 'monospace', marginTop: 18, color: bodyColor, maxWidth: 720 }}>
                  &gt; {c.purpose || bullets[0]?.text || 'RAW COMPUTATIONAL BLUEPRINT'}
                </div>
              </div>
            )}

            {/* Style 3: Apple Keynote Cover */}
            {style === 'keynote' && (
              <div style={{ textAlign: 'center', margin: 'auto 0' }}>
                <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.2em', color: accentColor, textTransform: 'uppercase' }}>
                  SPECIAL BRIEFING
                </span>
                <div style={{ fontSize: 52, fontWeight: 800, color: titleColor, lineHeight: 1.12, letterSpacing: '-0.03em', marginTop: 16 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 20, color: bodyColor, marginTop: 18, maxWidth: 680, margin: '18px auto 0', lineHeight: 1.45, opacity: 0.85 }}>
                  {c.purpose || bullets[0]?.text || 'Next-generation architecture and execution.'}
                </div>
              </div>
            )}

            {/* Style 4: Editorial Magazine Cover */}
            {style === 'editorial' && (
              <div>
                <div style={{ fontStyle: 'italic', fontSize: 15, color: accentColor, marginBottom: 12, letterSpacing: '0.04em' }}>
                  A Monograph on Strategic Direction —
                </div>
                <div style={{ fontSize: 46, fontWeight: 700, color: titleColor, lineHeight: 1.15, fontFamily: 'Playfair Display, serif', maxWidth: 820 }}>
                  {slide?.title}
                </div>
                <div style={{ width: 80, height: 1, background: borderCol, margin: '22px 0' }} />
                <div style={{ fontSize: 18, color: bodyColor, maxWidth: 700, lineHeight: 1.55, fontStyle: 'italic' }}>
                  “{c.purpose || bullets[0]?.text || 'Essays on creative autonomy and deliberate execution.'}”
                </div>
              </div>
            )}

            {/* Style 5: Japanese Minimalism Cover */}
            {style === 'japanese' && (
              <div style={{ borderLeft: `2px solid ${accentColor}`, paddingLeft: 32 }}>
                <div style={{ fontSize: 12, letterSpacing: '0.25em', color: accentColor, textTransform: 'uppercase', marginBottom: 16 }}>
                  間 • MA (NEGATIVE SPACE)
                </div>
                <div style={{ fontSize: 44, fontWeight: 600, color: titleColor, lineHeight: 1.25, letterSpacing: '0.02em', maxWidth: 740 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 17, color: bodyColor, marginTop: 24, maxWidth: 620, lineHeight: 1.6, opacity: 0.9 }}>
                  {c.purpose || bullets[0]?.text || 'Simplicity, balance, and intentional clarity.'}
                </div>
              </div>
            )}

            {/* Style 6: Cybersecurity / Terminal Cover */}
            {style === 'terminal' && (
              <div style={{ border: `1px solid ${borderCol}`, background: cardBg, borderRadius: radius, padding: 32 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, borderBottom: `1px solid ${borderCol}`, paddingBottom: 14, marginBottom: 24 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444' }} />
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#eab308' }} />
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981' }} />
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: accentColor, marginLeft: 8 }}>root@slidemind-core: ~ telemetry</span>
                </div>
                <div style={{ fontSize: 40, fontWeight: 800, color: titleColor, fontFamily: 'monospace', lineHeight: 1.15 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 15, fontFamily: 'monospace', color: bodyColor, marginTop: 16 }}>
                  [INITIALIZED] &gt; {c.purpose || bullets[0]?.text || 'Cryptographic telemetry & distributed mesh architecture'}
                </div>
              </div>
            )}

            {/* Style 7: Luxury Brand Cover */}
            {style === 'luxury' && (
              <div style={{ textAlign: 'center', margin: 'auto 0' }}>
                <div style={{ width: 40, height: 1, background: accentColor, margin: '0 auto 20px' }} />
                <div style={{ fontSize: 11, letterSpacing: '0.3em', color: accentColor, textTransform: 'uppercase', marginBottom: 16 }}>
                  HAUTE ÉDITION
                </div>
                <div style={{ fontSize: 46, fontWeight: 500, color: titleColor, letterSpacing: '0.12em', textTransform: 'uppercase', lineHeight: 1.2 }}>
                  {slide?.title}
                </div>
                <div style={{ width: 40, height: 1, background: accentColor, margin: '24px auto 16px' }} />
                <div style={{ fontSize: 14, color: bodyColor, letterSpacing: '0.08em', textTransform: 'uppercase', opacity: 0.8 }}>
                  {c.purpose || bullets[0]?.text || 'Mastery, craft, and enduring refinement'}
                </div>
              </div>
            )}

            {/* Style 8: Linear Precision Cover */}
            {style === 'linear' && (
              <div style={{ border: `1px solid ${borderCol}`, background: cardBg, borderRadius: radius, padding: 32 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: `1px solid ${borderCol}`, paddingBottom: 12, marginBottom: 20 }}>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: accentColor, fontWeight: 700 }}>
                    // SYSTEM: LINEAR_ENGINE_2026
                  </span>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: bodyColor }}>&lt;12MS P99</span>
                </div>
                <div style={{ fontSize: 46, fontWeight: 800, color: titleColor, letterSpacing: '-0.02em', lineHeight: 1.15 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 17, color: bodyColor, marginTop: 18, maxWidth: 740, lineHeight: 1.5 }}>
                  {c.purpose || bullets[0]?.text || 'Modular continuous deployment and distributed intelligence'}
                </div>
              </div>
            )}

            {/* Style 9: Stripe FinTech Cover */}
            {style === 'fintech' && (
              <div>
                <span style={{ padding: '4px 12px', borderRadius: 99, background: `${accentColor}18`, border: `1px solid ${accentColor}40`, color: accentColor, fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  FINANCIAL ARCHITECTURE
                </span>
                <div style={{ fontSize: 48, fontWeight: 900, color: titleColor, lineHeight: 1.12, letterSpacing: '-0.03em', marginTop: 16, maxWidth: 840 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 19, color: bodyColor, marginTop: 16, maxWidth: 760, lineHeight: 1.45 }}>
                  {c.purpose || bullets[0]?.text || 'Global liquidity and real-time transaction processing'}
                </div>
              </div>
            )}

            {/* Style 10: Pitch Venture Cover */}
            {style === 'pitch' && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                  <span style={{ background: '#10b98125', border: '1px solid #10b98150', color: '#10b981', padding: '4px 10px', borderRadius: 99, fontSize: 10, fontWeight: 800, textTransform: 'uppercase' }}>
                    SERIES A PITCH
                  </span>
                  <span style={{ color: '#10b981', fontSize: 11, fontWeight: 800, fontFamily: 'monospace' }}>+310% NDR</span>
                </div>
                <div style={{ fontSize: 50, fontWeight: 900, color: titleColor, lineHeight: 1.1, letterSpacing: '-0.03em', maxWidth: 820 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 19, color: bodyColor, marginTop: 16, maxWidth: 740, lineHeight: 1.45, opacity: 0.9 }}>
                  {c.purpose || bullets[0]?.text || 'Solving enterprise friction through ambient workflow intelligence'}
                </div>
              </div>
            )}

            {/* Default Cover */}
            {!['swiss', 'brutalist', 'keynote', 'editorial', 'japanese', 'terminal', 'luxury', 'linear', 'fintech', 'pitch'].includes(style) && (
              <div>
                <div style={{ width: 80, height: 4, background: accentColor, borderRadius: 2, marginBottom: 24 }} />
                <div style={{ fontSize: 46, fontWeight: 800, color: titleColor, lineHeight: 1.15, letterSpacing: '-0.02em', maxWidth: 840 }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 20, color: bodyColor, marginTop: 18, maxWidth: 760, lineHeight: 1.45 }}>
                  {c.purpose || bullets[0]?.text || 'Strategic presentation & verified insights'}
                </div>
                <div style={{ marginTop: 32, display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: radius, background: cardBg, border: `1px solid ${borderCol}` }}>
                  <Zap size={14} color={accentColor} />
                  <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: accentColor, textTransform: 'uppercase' }}>
                    {ds.name}
                  </span>
                </div>
              </div>
            )}
            </div>

            {/* Photographic Attribution Pill */}
            {c.image?.artist && (
              <div
                style={{
                  position: 'absolute',
                  bottom: -16,
                  right: -24,
                  zIndex: 3,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '3px 8px',
                  borderRadius: 4,
                  background: 'rgba(0,0,0,0.45)',
                  backdropFilter: 'blur(4px)',
                  color: 'rgba(255,255,255,0.85)',
                  fontSize: 10,
                  letterSpacing: '0.04em',
                }}
              >
                <span>Photo: {c.image.artist}</span>
                <span>•</span>
                <span>{c.image.source || 'Verified Visual'}</span>
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* INNER SLIDES (Non-Hero)                                  */}
        {/* ========================================================= */}
        {layout !== 'full_bleed_hero' && !first && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* 1. Swiss Inner Slide Header */}
            {style === 'swiss' && (
              <div style={{ borderBottom: `2px solid ${titleColor}`, paddingBottom: 14, marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div style={{ fontSize: 32, fontWeight: 900, color: titleColor, letterSpacing: '-0.02em' }}>
                  {slide?.title}
                </div>
                <div style={{ fontSize: 14, fontWeight: 800, color: accentColor }}>
                  NO. {String(slide?.position || 1).padStart(2, '0')}
                </div>
              </div>
            )}

            {/* 2. Brutalist Inner Slide Header */}
            {style === 'brutalist' && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: `2px solid ${titleColor}`, padding: '8px 16px', background: accentColor, marginBottom: 20 }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: '#000000', textTransform: 'uppercase', fontFamily: 'monospace' }}>
                  {slide?.title}
                </div>
                <span style={{ fontSize: 12, fontWeight: 900, fontFamily: 'monospace', color: '#000000' }}>
                  [{String(slide?.position || 1).padStart(2, '0')}]
                </span>
              </div>
            )}

            {/* 3. Terminal Inner Slide Header */}
            {style === 'terminal' && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${borderCol}`, paddingBottom: 12, marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Terminal size={18} color={accentColor} />
                  <span style={{ fontSize: 22, fontWeight: 700, color: titleColor, fontFamily: 'monospace' }}>
                    &gt; {slide?.title}
                  </span>
                </div>
                <span style={{ fontSize: 12, fontFamily: 'monospace', color: accentColor }}>
                  [NODE_{String(slide?.position || 1).padStart(2, '0')}]
                </span>
              </div>
            )}

            {/* Standard Header for all other styles */}
            {!['swiss', 'brutalist', 'terminal'].includes(style) && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 8, height: 8, borderRadius: radius > 8 ? '50%' : 0, background: accentColor }} />
                  <div style={{ fontSize: 28, fontWeight: 800, color: titleColor, letterSpacing: '-0.01em' }}>
                    {slide?.title}
                  </div>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: accentColor }}>
                  #{String(slide?.position || 1).padStart(2, '0')}
                </div>
              </div>
            )}

            {/* SLIDE CONTENT RENDERING */}
            <div style={{ flex: 1, minHeight: 0 }}>
              {renderAdvancedLayout(layout, {
                slide,
                content: c,
                title: slide?.title,
                theme: {
                  primary: titleColor,
                  secondary: bodyColor,
                  accent: accentColor,
                  cardBg,
                  border: borderCol,
                  cardRadius: radius,
                  muted: ds.muted,
                  isDark: ds.isDark,
                },
                bullets,
              }) || (
                <>
              {/* LAYOUT: Stats & KPI */}
              {layout === 'stats_kpi' && (
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(3, Math.max(1, (c.kpis || bullets).length))}, 1fr)`, gap: 18, height: '85%' }}>
                  {((c.kpis && c.kpis.length > 0) ? c.kpis : bullets.map((b, i) => ({ value: '10x', label: `Metric ${i+1}`, description: b.text }))).slice(0, 3).map((kpi, i) => (
                    <div
                      key={i}
                      style={{
                        background: cardBg,
                        border: style === 'brutalist' ? `2px solid ${titleColor}` : `1px solid ${borderCol}`,
                        borderRadius: radius,
                        padding: '24px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        boxSizing: 'border-box',
                      }}
                    >
                      <div style={{ fontSize: 44, fontWeight: 900, color: accentColor, letterSpacing: '-0.03em' }}>{kpi.value}</div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 800, textTransform: 'uppercase', color: titleColor, letterSpacing: '0.05em', marginBottom: 8 }}>{kpi.label}</div>
                        <div style={{ fontSize: 13, color: bodyColor, lineHeight: 1.45, opacity: 0.9 }}>{kpi.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* LAYOUT: Cards Hierarchy / Columns */}
              {(layout === 'cards_hierarchy' || layout === 'two_column') && (
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(3, Math.max(1, (c.cards || bullets).length))}, 1fr)`, gap: 18, height: '85%' }}>
                  {((c.cards && c.cards.length > 0) ? c.cards : bullets.map((b, i) => ({ title: `Pillar ${i+1}`, description: b.text, badge: `0${i+1}` }))).slice(0, 3).map((card, i) => (
                    <div
                      key={i}
                      style={{
                        background: cardBg,
                        border: style === 'brutalist' ? `2px solid ${titleColor}` : `1px solid ${borderCol}`,
                        borderRadius: radius,
                        padding: '24px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: accentColor, letterSpacing: '0.08em' }}>// {card.badge || `0${i+1}`}</span>
                        <Zap size={15} color={accentColor} />
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: titleColor, marginBottom: 10, lineHeight: 1.3 }}>{card.title}</div>
                      <div style={{ fontSize: 13, color: bodyColor, lineHeight: 1.5, opacity: 0.9 }}>{card.description}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* LAYOUT: Problem vs Solution */}
              {layout === 'problem_solution' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, height: '85%' }}>
                  <div style={{ background: cardBg, border: `1px solid ${borderCol}`, borderRadius: radius, padding: 24 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#ef4444', fontWeight: 800, fontSize: 12, textTransform: 'uppercase', marginBottom: 16 }}>
                      <AlertTriangle size={15} /> The Problem & Friction
                    </div>
                    {(c.problem?.points || bullets.slice(0, 2)).map((p, i) => (
                      <div key={i} style={{ fontSize: 13, color: bodyColor, margin: '12px 0', lineHeight: 1.45, display: 'flex', gap: 8 }}>
                        <span style={{ color: '#ef4444', fontWeight: 800 }}>✕</span>
                        <span>{typeof p === 'string' ? p : p.text}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ background: cardBg, border: `1px solid ${borderCol}`, borderRadius: radius, padding: 24 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', fontWeight: 800, fontSize: 12, textTransform: 'uppercase', marginBottom: 16 }}>
                      <CheckCircle2 size={15} /> The Breakthrough Solution
                    </div>
                    {(c.solution?.points || bullets.slice(2, 4)).map((p, i) => (
                      <div key={i} style={{ fontSize: 13, color: bodyColor, margin: '12px 0', lineHeight: 1.45, display: 'flex', gap: 8 }}>
                        <span style={{ color: '#10b981', fontWeight: 800 }}>✓</span>
                        <span>{typeof p === 'string' ? p : p.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* LAYOUT: Process Diagram / Steps */}
              {(layout === 'process_diagram' || layout === 'timeline') && (
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(4, Math.max(1, (c.process_steps || bullets).length))}, 1fr)`, gap: 16, height: '85%' }}>
                  {((c.process_steps && c.process_steps.length > 0) ? c.process_steps : bullets.map((b, i) => ({ step_number: i+1, title: `Phase ${i+1}`, description: b.text }))).slice(0, 4).map((st, i) => (
                    <div
                      key={i}
                      style={{
                        background: cardBg,
                        border: style === 'brutalist' ? `2px solid ${titleColor}` : `1px solid ${borderCol}`,
                        borderRadius: radius,
                        padding: 18,
                        display: 'flex',
                        flexDirection: 'column',
                      }}
                    >
                      <div style={{ width: 32, height: 32, borderRadius: radius > 4 ? '50%' : 0, background: accentColor, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13, marginBottom: 12 }}>
                        {st.step_number || i + 1}
                      </div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: titleColor, marginBottom: 8 }}>{st.title}</div>
                      <div style={{ fontSize: 12, color: bodyColor, lineHeight: 1.45, opacity: 0.9 }}>{st.description}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* LAYOUT: Quote / Testimonial */}
              {layout === 'quote_testimonial' && (
                <div style={{ background: cardBg, border: `1px solid ${borderCol}`, borderRadius: radius, padding: '36px 44px', height: '85%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <div style={{ fontSize: 50, lineHeight: 0.8, color: accentColor, fontFamily: 'Georgia, serif' }}>“</div>
                  <div style={{ fontSize: 24, fontWeight: 500, color: titleColor, lineHeight: 1.4, margin: '14px 0', fontStyle: 'italic' }}>
                    {c.quote?.text || bullets[0]?.text || slide?.title}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
                    <div style={{ width: 28, height: 2, background: accentColor }} />
                    <div style={{ fontSize: 14, fontWeight: 700, color: titleColor }}>{c.quote?.author || 'Key Strategic Takeaway'}</div>
                    <div style={{ fontSize: 12, color: bodyColor, opacity: 0.7 }}>• {c.quote?.role || 'Executive Finding'}</div>
                  </div>
                </div>
              )}

              {/* LAYOUT: Chart */}
              {layout === 'chart' && c.chart && (
                <div style={{ background: cardBg, border: `1px solid ${borderCol}`, borderRadius: radius, padding: 20, height: '85%' }}>
                  <Chart chart={c.chart} color={bodyColor} />
                </div>
              )}

              {/* LAYOUT: Diagram */}
              {layout === 'diagram' && c.diagram && (
                <div style={{ background: cardBg, border: `1px solid ${borderCol}`, borderRadius: radius, padding: 20, height: '85%' }}>
                  <Diagram diagram={c.diagram} color={bodyColor} />
                </div>
              )}

              {/* LAYOUT: Split Screen (Photographic or Diagram Split) */}
              {layout === 'split_screen' && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: c.image?.composition === 'split_left' ? '1.15fr 1fr' : '1fr 1.15fr',
                    gap: 24,
                    height: '86%',
                    alignItems: 'stretch',
                  }}
                >
                  {/* Left Column: Structured Narrative Content */}
                  <div
                    style={{
                      order: c.image?.composition === 'split_left' ? 2 : 1,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                      background: cardBg,
                      border: style === 'brutalist' ? `2px solid ${titleColor}` : `1px solid ${borderCol}`,
                      borderRadius: radius,
                      padding: '24px 28px',
                      boxSizing: 'border-box',
                      minWidth: 0,
                      overflow: 'hidden',
                    }}
                  >
                    <div style={{ fontSize: 11, fontWeight: 800, color: accentColor, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>
                      // Core Synthesis & Findings
                    </div>
                    {bullets.slice(0, 4).map((b, i) => (
                      <div key={i} style={{ fontSize: 14, color: bodyColor, margin: '8px 0', lineHeight: 1.5, display: 'flex', gap: 10 }}>
                        <span style={{ color: accentColor, fontWeight: 800 }}>•</span>
                        <span style={{ wordBreak: 'break-word', minWidth: 0 }}>{typeof b === 'string' ? b : b.text}</span>
                      </div>
                    ))}
                  </div>

                  {/* Right Column: Visual Frame with attribution */}
                  <div
                    style={{
                      order: c.image?.composition === 'split_left' ? 1 : 2,
                      display: 'flex',
                      flexDirection: 'column',
                      height: '100%',
                      background: cardBg,
                      border: style === 'brutalist' ? `2px solid ${titleColor}` : `1px solid ${borderCol}`,
                      borderRadius: radius,
                      overflow: 'hidden',
                      position: 'relative',
                      minWidth: 0,
                      boxShadow: '0 4px 20px rgba(0,0,0,0.06)',
                    }}
                  >
                    {c.image?.url ? (
                      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                        <img
                          src={c.image.url}
                          alt={c.image.alt || slide?.title}
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                          }}
                          onError={(e) => {
                            e.currentTarget.style.display = 'none'
                          }}
                        />
                        {c.image?.artist && (
                          <div
                            style={{
                              position: 'absolute',
                              bottom: 0,
                              left: 0,
                              right: 0,
                              padding: '6px 12px',
                              background: 'rgba(0,0,0,0.68)',
                              backdropFilter: 'blur(4px)',
                              color: '#ffffff',
                              fontSize: 10,
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <span style={{ opacity: 0.9 }}>
                              Photo: {c.image.artist}
                            </span>
                            <span style={{ opacity: 0.75, fontSize: 9 }}>
                              {c.image.license ? c.image.license.slice(0, 22) : c.image.source}
                            </span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div
                        style={{
                          flex: 1,
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'center',
                          alignItems: 'center',
                          background: ds.isDark
                            ? 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)'
                            : 'linear-gradient(135deg, rgba(0,0,0,0.03) 0%, rgba(0,0,0,0.01) 100%)',
                          padding: 24,
                          textAlign: 'center',
                          position: 'relative',
                        }}
                      >
                        <div
                          style={{
                            width: 48,
                            height: 48,
                            borderRadius: radius,
                            background: `${accentColor}18`,
                            border: `1px solid ${accentColor}33`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            marginBottom: 16,
                          }}
                        >
                          <Compass size={24} color={accentColor} />
                        </div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: titleColor, maxWidth: 260, lineHeight: 1.3 }}>
                          {slide?.title}
                        </div>
                        <div style={{ fontSize: 11, color: ds.muted, marginTop: 8, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                          Strategic Horizon
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* LAYOUT: Image Gallery / Visual Showcase */}
              {layout === 'image_gallery' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 20, height: '86%' }}>
                  <div style={{ borderRadius: radius, overflow: 'hidden', border: `1px solid ${borderCol}`, position: 'relative', background: cardBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {c.image?.url ? (
                      <img
                        src={c.image.url}
                        alt={c.image.alt || slide?.title}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : (
                      <div style={{ textAlign: 'center', padding: 24 }}>
                        <div style={{ width: 44, height: 44, borderRadius: radius, background: `${accentColor}18`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
                          <Compass size={22} color={accentColor} />
                        </div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: titleColor }}>{slide?.title}</div>
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {bullets.slice(0, 3).map((b, i) => (
                      <div key={i} style={{ flex: 1, background: cardBg, border: `1px solid ${borderCol}`, borderRadius: radius, padding: '14px 18px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: accentColor }}>// SPEC 0{i+1}</span>
                        <span style={{ fontSize: 13, color: bodyColor, marginTop: 4 }}>{typeof b === 'string' ? b : b.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Fallback Standard Layout */}
              {!['stats_kpi', 'cards_hierarchy', 'two_column', 'problem_solution', 'process_diagram', 'timeline', 'quote_testimonial', 'chart', 'diagram', 'split_screen', 'image_gallery'].includes(layout) && (
                <div style={{ background: cardBg, border: style === 'brutalist' ? `2px solid ${titleColor}` : `1px solid ${borderCol}`, borderRadius: radius, padding: '24px 32px', height: '85%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  {bullets.slice(0, 5).map((b, i) => (
                    <div key={i} style={{ fontSize: 16, color: bodyColor, margin: '8px 0', lineHeight: 1.45, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                      <span style={{ color: accentColor, fontWeight: 800, fontSize: 18, lineHeight: 1 }}>
                        {style === 'swiss' ? `0${i+1}.` : '•'}
                      </span>
                      <span>{b.text}</span>
                    </div>
                  ))}
                </div>
              )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

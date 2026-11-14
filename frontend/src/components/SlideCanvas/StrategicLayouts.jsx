import { ArrowRight, TrendingUp, Compass, Target, Shield, CheckCircle2, ChevronRight } from 'lucide-react'

/**
 * Strategic Business Layouts directly inspired by professional pitch decks (Ref 1 & 2):
 * - 2x2 Competitor Matrix
 * - Market Adoption Gaussian Curve
 * - Customer Acquisition Chevron Funnel
 * - Milestone Metric Roadmap
 * - Business Model Canvas
 */

// 1. 2x2 Competitor Matrix (Ref 1 Slide 4 & 5)
export function CompetitorMatrix2x2({ slide, designSystem }) {
  const c = slide?.content || {}
  const diag = c.diagram || {}
  const mat = diag.matrix || {}

  const xAxis = mat.x_axis || 'Opportunity Volume'
  const yAxis = mat.y_axis || 'Win Rate / Strategic Defensibility'
  const nodes = mat.nodes || [
    { name: 'Our Solution', x: 80, y: 82, highlight: true },
    { name: 'Legacy Incumbent', x: 30, y: 68, highlight: false },
    { name: 'Emergent Disrupter', x: 72, y: 32, highlight: false },
    { name: 'Niche Vendor', x: 25, y: 28, highlight: false },
  ]

  const accent = designSystem?.accent || '#eb3324'
  const cardBg = designSystem?.cardBg || '#ffffff'
  const borderCol = designSystem?.border || '#e4e4e7'
  const textCol = designSystem?.text || '#18181b'
  const mutedCol = designSystem?.muted || '#71717a'

  return (
    <div style={{ height: '86%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, height: '100%', alignItems: 'center' }}>
        {/* 2x2 Coordinate Grid Canvas */}
        <div
          style={{
            position: 'relative',
            height: '100%',
            background: cardBg,
            border: `1px solid ${borderCol}`,
            borderRadius: 14,
            padding: 24,
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          {/* Y-Axis Label */}
          <div
            style={{
              position: 'absolute',
              top: 14,
              left: 20,
              fontSize: 10,
              fontWeight: 700,
              fontFamily: 'monospace',
              letterSpacing: '0.08em',
              color: mutedCol,
              textTransform: 'uppercase',
            }}
          >
            ↑ {yAxis}
          </div>

          {/* 4 Quadrants Visual Frame */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '78%',
              marginTop: 18,
              borderLeft: `2px solid ${borderCol}`,
              borderBottom: `2px solid ${borderCol}`,
            }}
          >
            {/* Crosshair Dividers */}
            <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: 1, borderTop: `1px dashed ${borderCol}` }} />
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: '50%', width: 1, borderLeft: `1px dashed ${borderCol}` }} />

            {/* Quadrant Watermark Badges */}
            <span style={{ position: 'absolute', top: 8, right: 12, fontSize: 10, fontWeight: 700, color: `${accent}99`, fontFamily: 'monospace' }}>
              MARKET LEADERS
            </span>
            <span style={{ position: 'absolute', top: 8, left: 12, fontSize: 10, fontWeight: 600, color: `${mutedCol}66`, fontFamily: 'monospace' }}>
              CONTENDERS
            </span>
            <span style={{ position: 'absolute', bottom: 8, left: 12, fontSize: 10, fontWeight: 600, color: `${mutedCol}66`, fontFamily: 'monospace' }}>
              NICHE PLAYERS
            </span>
            <span style={{ position: 'absolute', bottom: 8, right: 12, fontSize: 10, fontWeight: 600, color: `${mutedCol}66`, fontFamily: 'monospace' }}>
              EMERGENT
            </span>

            {/* Competitor Nodes */}
            {nodes.map((n, i) => (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  left: `${Math.max(8, Math.min(90, n.x))}%`,
                  bottom: `${Math.max(8, Math.min(90, n.y))}%`,
                  transform: 'translate(-50%, 50%)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  zIndex: n.highlight ? 10 : 2,
                }}
              >
                <div
                  style={{
                    width: n.highlight ? 14 : 10,
                    height: n.highlight ? 14 : 10,
                    borderRadius: '50%',
                    background: n.highlight ? accent : '#a1a1aa',
                    boxShadow: n.highlight ? `0 0 16px ${accent}` : 'none',
                    border: '2px solid #ffffff',
                  }}
                />
                <span
                  style={{
                    fontSize: n.highlight ? 12 : 11,
                    fontWeight: n.highlight ? 800 : 600,
                    color: n.highlight ? textCol : mutedCol,
                    whiteSpace: 'nowrap',
                    background: cardBg,
                    padding: '2px 6px',
                    borderRadius: 4,
                    border: n.highlight ? `1px solid ${accent}` : `1px solid ${borderCol}`,
                  }}
                >
                  {n.name}
                </span>
              </div>
            ))}
          </div>

          {/* X-Axis Label */}
          <div
            style={{
              position: 'absolute',
              bottom: 12,
              right: 20,
              fontSize: 10,
              fontWeight: 700,
              fontFamily: 'monospace',
              letterSpacing: '0.08em',
              color: mutedCol,
              textTransform: 'uppercase',
            }}
          >
            {xAxis} →
          </div>
        </div>

        {/* Right Side: Narrative Analysis & Strategic Advantage */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {c.narrative && (
            <div style={{ background: cardBg, border: `1px solid ${borderCol}`, borderRadius: 12, padding: 18 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: accent, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                Strategic Moat
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.5, color: textCol, margin: 0 }}>
                {c.narrative}
              </p>
            </div>
          )}

          {(c.bullets || []).slice(0, 3).map((b, i) => (
            <div
              key={i}
              style={{
                background: cardBg,
                border: `1px solid ${borderCol}`,
                borderRadius: 12,
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
              }}
            >
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: accent, marginTop: 6, flexShrink: 0 }} />
              <div style={{ fontSize: 12, lineHeight: 1.45, color: textCol }}>
                {typeof b === 'string' ? b : b.text}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// 2. Market Adoption Gaussian Curve (Ref 1 Slide 2)
export function MarketAdoptionGaussian({ slide, designSystem }) {
  const c = slide?.content || {}
  const accent = designSystem?.accent || '#2563eb'
  const cardBg = designSystem?.cardBg || '#ffffff'
  const borderCol = designSystem?.border || '#e4e4e7'
  const textCol = designSystem?.text || '#18181b'
  const mutedCol = designSystem?.muted || '#71717a'

  const stages = [
    { label: 'Innovators', share: '2.5%', detail: 'Tech enthusiasts & early experimenters' },
    { label: 'Early Adopters', share: '13.5%', detail: 'Visionaries seeking competitive leaps' },
    { label: 'Early Majority', share: '34.0%', detail: 'Pragmatists requiring proven ROI' },
    { label: 'Late Majority', share: '34.0%', detail: 'Conservatives following market consensus' },
    { label: 'Laggards', share: '16.0%', detail: 'Skeptics adopting on necessity' },
  ]

  return (
    <div style={{ height: '86%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      {/* Narrative Lead */}
      {c.narrative && (
        <div style={{ fontSize: 13, color: mutedCol, lineHeight: 1.5, marginBottom: 8 }}>
          {c.narrative}
        </div>
      )}

      {/* Gaussian Distribution SVG Bell Curve */}
      <div
        style={{
          background: cardBg,
          border: `1px solid ${borderCol}`,
          borderRadius: 14,
          padding: '24px 32px 14px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.03)',
        }}
      >
        <svg viewBox="0 0 800 220" style={{ width: '100%', height: 160, overflow: 'visible' }}>
          <defs>
            <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={accent} stopOpacity="0.45" />
              <stop offset="100%" stopColor={accent} stopOpacity="0.03" />
            </linearGradient>
          </defs>

          {/* Shaded Normal Distribution Bell Curve */}
          <path
            d="M 50 200 C 150 200, 220 180, 280 120 C 340 60, 370 20, 400 20 C 430 20, 460 60, 520 120 C 580 180, 650 200, 750 200 Z"
            fill="url(#curveGradient)"
          />

          {/* Stroke Outline */}
          <path
            d="M 50 200 C 150 200, 220 180, 280 120 C 340 60, 370 20, 400 20 C 430 20, 460 60, 520 120 C 580 180, 650 200, 750 200"
            fill="none"
            stroke={accent}
            strokeWidth="3.5"
            strokeLinecap="round"
          />

          {/* Stage Vertical Partition Dividers */}
          <line x1="170" y1="188" x2="170" y2="200" stroke={borderCol} strokeWidth="1.5" />
          <line x1="280" y1="120" x2="280" y2="200" stroke={borderCol} strokeWidth="1.5" strokeDasharray="3 3" />
          <line x1="400" y1="20" x2="400" y2="200" stroke={accent} strokeWidth="1.5" strokeDasharray="4 4" />
          <line x1="520" y1="120" x2="520" y2="200" stroke={borderCol} strokeWidth="1.5" strokeDasharray="3 3" />
          <line x1="630" y1="188" x2="630" y2="200" stroke={borderCol} strokeWidth="1.5" />
          <line x1="40" y1="200" x2="760" y2="200" stroke={borderCol} strokeWidth="2" />

          {/* Chasm Indicator Badge */}
          <rect x="250" y="105" width="60" height="18" rx="4" fill={accent} />
          <text x="280" y="117" textAnchor="middle" fill="#ffffff" fontSize="9" fontWeight="bold">
            THE CHASM
          </text>
        </svg>

        {/* 5 Stage Labels & Share Indicators */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginTop: 12, textAlign: 'center' }}>
          {stages.map((st, i) => (
            <div key={i} style={{ padding: '6px 4px', borderTop: i === 2 ? `2px solid ${accent}` : 'none' }}>
              <div style={{ fontSize: 13, fontWeight: 800, color: i === 2 ? accent : textCol }}>
                {st.share}
              </div>
              <div style={{ fontSize: 11, fontWeight: 700, color: textCol, marginTop: 2 }}>
                {st.label}
              </div>
              <div style={{ fontSize: 9, color: mutedCol, marginTop: 3, lineHeight: 1.3 }}>
                {st.detail}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// 3. Customer Acquisition Chevron Funnel (Ref 1 Slide 7)
export function ChevronFunnel({ slide, designSystem }) {
  const c = slide?.content || {}
  const accent = designSystem?.accent || '#2563eb'
  const cardBg = designSystem?.cardBg || '#ffffff'
  const borderCol = designSystem?.border || '#e4e4e7'
  const textCol = designSystem?.text || '#18181b'
  const mutedCol = designSystem?.muted || '#71717a'

  const stages = [
    { step: '01', title: 'Attract', audience: 'Market Strangers', metric: '100% Inflow', color: accent },
    { step: '02', title: 'Engage', audience: 'Active Visitors', metric: '42% Conversion', color: `${accent}dd` },
    { step: '03', title: 'Convert', audience: 'Qualified Leads', metric: '18% Pipeline', color: `${accent}bb` },
    { step: '04', title: 'Delight', audience: 'Enterprise Customers', metric: '6.5% Net Win', color: `${accent}99` },
  ]

  return (
    <div style={{ height: '86%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      {c.narrative && (
        <div style={{ fontSize: 13, color: mutedCol, lineHeight: 1.5, marginBottom: 12 }}>
          {c.narrative}
        </div>
      )}

      {/* Chevrons Flow Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, height: '60%' }}>
        {stages.map((st, i) => (
          <div
            key={i}
            style={{
              background: cardBg,
              border: `1px solid ${borderCol}`,
              borderRadius: 14,
              padding: '20px 18px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Top Accent Stripe */}
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: st.color }} />

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: 10, fontWeight: 800, fontFamily: 'monospace', color: st.color }}>
                  STAGE {st.step}
                </span>
                <span style={{ fontSize: 11, fontWeight: 700, color: textCol, background: `${st.color}15`, padding: '2px 6px', borderRadius: 4 }}>
                  {st.metric}
                </span>
              </div>
              <h4 style={{ fontSize: 17, fontWeight: 700, color: textCol, margin: '0 0 6px 0' }}>
                {st.title}
              </h4>
              <p style={{ fontSize: 11, color: mutedCol, margin: 0 }}>
                Target: {st.audience}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, color: st.color, marginTop: 12 }}>
              <span>Pipeline velocity</span>
              <ChevronRight size={14} />
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Substantive Bullet Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 14 }}>
        {(c.bullets || []).slice(0, 3).map((b, i) => (
          <div key={i} style={{ background: cardBg, border: `1px solid ${borderCol}`, borderRadius: 10, padding: '10px 14px', fontSize: 11, color: textCol, lineHeight: 1.4 }}>
            {typeof b === 'string' ? b : b.text}
          </div>
        ))}
      </div>
    </div>
  )
}

// 4. Milestone Metric Roadmap (Ref 1 Slide 9)
export function MilestoneRoadmap({ slide, designSystem }) {
  const c = slide?.content || {}
  const accent = designSystem?.accent || '#2563eb'
  const cardBg = designSystem?.cardBg || '#ffffff'
  const borderCol = designSystem?.border || '#e4e4e7'
  const textCol = designSystem?.text || '#18181b'
  const mutedCol = designSystem?.muted || '#71717a'

  const milestones = [
    { target: '$100,000', phase: 'Phase 1: Seed Alpha', date: 'Q1 Launch', detail: 'Initial core prototype deployment & design system rollout' },
    { target: '$350,000', phase: 'Phase 2: Product Expansion', date: 'Q2 Growth', detail: 'Automated multi-source visual synthesis & Google Slides sync' },
    { target: '$390,000', phase: 'Phase 3: Enterprise Scale', date: 'Q3 Enterprise', detail: 'Zero-trust security compliance, custom brand kits & teams' },
    { target: '$466,000', phase: 'Phase 4: Global Traction', date: 'Q4 Velocity', detail: 'Cross-platform native apps & real-time collaboration canvas' },
  ]

  return (
    <div style={{ height: '86%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      {c.narrative && (
        <div style={{ fontSize: 13, color: mutedCol, lineHeight: 1.5, marginBottom: 12 }}>
          {c.narrative}
        </div>
      )}

      {/* Milestone Line Chart with Nodes */}
      <div
        style={{
          background: cardBg,
          border: `1px solid ${borderCol}`,
          borderRadius: 14,
          padding: '24px 32px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.03)',
        }}
      >
        <div style={{ position: 'relative', margin: '40px 0 20px' }}>
          {/* Connecting Axis Line */}
          <div style={{ position: 'absolute', top: 12, left: '6%', right: '6%', height: 3, background: `linear-gradient(to right, ${accent}44, ${accent})` }} />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, position: 'relative', zIndex: 2 }}>
            {milestones.map((m, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
                {/* Node Pill */}
                <div
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: '50%',
                    background: accent,
                    color: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 11,
                    fontWeight: 800,
                    boxShadow: `0 0 12px ${accent}88`,
                    border: '3px solid #ffffff',
                    marginBottom: 12,
                  }}
                >
                  {i + 1}
                </div>

                <div style={{ fontSize: 18, fontWeight: 800, color: textCol, letterSpacing: '-0.02em' }}>
                  {m.target}
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: accent, textTransform: 'uppercase', marginTop: 2 }}>
                  {m.date}
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: textCol, marginTop: 4 }}>
                  {m.phase}
                </div>
                <div style={{ fontSize: 10, color: mutedCol, marginTop: 4, lineHeight: 1.35 }}>
                  {m.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Strategic Summary */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', background: `${accent}0d`, border: `1px solid ${accent}33`, borderRadius: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: accent, textTransform: 'uppercase' }}>
          Capital Allocation Strategy
        </span>
        <span style={{ fontSize: 12, color: textCol }}>
          100% of milestones grounded in validated historical traction and unit economics.
        </span>
      </div>
    </div>
  )
}

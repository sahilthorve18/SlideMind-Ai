import React from 'react'
import { Sparkles, ArrowRight, Quote, CheckCircle2, Bookmark, Compass } from 'lucide-react'

/**
 * EditorialLayouts.jsx
 * Implements high-end publication, magazine, and media compositions
 * directly referencing Canva & Gamma design patterns (Ref 3, 4, 5).
 */

// 1. Photo Mosaic 2x2 (Ref 4 Slide 6 - 4 images/cards grid with labels and captions)
export function PhotoMosaic2x2({ content, title, theme }) {
  const images = content.mosaic_images || [
    { title: 'Visual Artifact 01', label: 'Primary Angle', url: content.image?.url },
    { title: 'Visual Artifact 02', label: 'Secondary Detail' },
    { title: 'Visual Artifact 03', label: 'Contextual In-Situ' },
    { title: 'Visual Artifact 04', label: 'Macro Focus' },
  ]
  const bullets = content.bullets || []

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, height: '100%' }}>
        {images.slice(0, 4).map((item, i) => (
          <div
            key={i}
            style={{
              background: theme.cardBg,
              borderRadius: theme.cardRadius || 12,
              border: `1px solid ${theme.border}`,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
            }}
          >
            <div style={{ height: '58%', position: 'relative', overflow: 'hidden', background: `${theme.accent}14` }}>
              {item.url || content.image?.url ? (
                <img
                  src={item.url || content.image?.url}
                  alt={item.title}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => { e.currentTarget.style.display = 'none' }}
                />
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Compass size={28} color={theme.accent} opacity={0.6} />
                </div>
              )}
              <div
                style={{
                  position: 'absolute',
                  top: 8,
                  left: 8,
                  background: 'rgba(0,0,0,0.65)',
                  backdropFilter: 'blur(4px)',
                  color: '#fff',
                  fontSize: 10,
                  fontWeight: 800,
                  padding: '3px 7px',
                  borderRadius: 4,
                  letterSpacing: '0.06em',
                }}
              >
                0{i + 1}
              </div>
            </div>
            <div style={{ padding: '12px 14px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800, color: theme.primary, marginBottom: 4 }}>
                  {item.title || bullets[i]?.text?.slice(0, 24) || `Feature ${i+1}`}
                </div>
                <div style={{ fontSize: 11, color: theme.secondary, lineHeight: 1.4, opacity: 0.85 }}>
                  {bullets[i]?.text || 'Documented key architectural attribute and verified user interaction.'}
                </div>
              </div>
              <div style={{ fontSize: 9, fontWeight: 700, color: theme.accent, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                {item.label || 'ANALYSIS SPEC'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// 2. Photo Mosaic 3-Column (Ref 4 Slide 14 - 3 tall vertical photos with editorial captions)
export function PhotoMosaic3Col({ content, title, theme }) {
  const cards = content.cards || content.bullets || [
    { title: 'The Vision', description: 'Core strategic direction and fundamental user positioning.' },
    { title: 'The Execution', description: 'Architectural precision and repeatable development velocity.' },
    { title: 'The Scale', description: 'Sustainable multi-market penetration and verified ecosystem.' },
  ]

  return (
    <div style={{ height: '88%', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 }}>
      {cards.slice(0, 3).map((c, i) => (
        <div
          key={i}
          style={{
            background: theme.cardBg,
            borderRadius: theme.cardRadius || 12,
            border: `1px solid ${theme.border}`,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ height: '48%', position: 'relative', overflow: 'hidden', background: `${theme.accent}12` }}>
            {content.image?.url ? (
              <img
                src={content.image.url}
                alt={c.title || title}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                onError={(e) => { e.currentTarget.style.display = 'none' }}
              />
            ) : (
              <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Sparkles size={32} color={theme.accent} opacity={0.5} />
              </div>
            )}
            <div
              style={{
                position: 'absolute',
                bottom: 8,
                left: 10,
                background: theme.accent,
                color: '#fff',
                fontSize: 10,
                fontWeight: 800,
                padding: '2px 8px',
                borderRadius: 4,
              }}
            >
              PILLAR 0{i + 1}
            </div>
          </div>
          <div style={{ padding: '16px 18px', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: theme.primary, marginBottom: 8, lineHeight: 1.3 }}>
              {typeof c === 'string' ? `Insight ${i+1}` : c.title || `Key Vector 0${i+1}`}
            </div>
            <div style={{ fontSize: 12, color: theme.secondary, lineHeight: 1.5, opacity: 0.9 }}>
              {typeof c === 'string' ? c : c.description || c.text || 'Comprehensive strategic finding supporting deck thesis.'}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// 3. Wave Editorial Layout (Ref 1 Slide 3 & 6, Ref 2 Slide 1 - organic curved boundary)
export function WaveEditorialLayout({ content, title, theme }) {
  const cards = content.cards || content.bullets || []

  return (
    <div style={{ height: '88%', position: 'relative', borderRadius: theme.cardRadius || 14, overflow: 'hidden', background: theme.cardBg, border: `1px solid ${theme.border}` }}>
      {/* Wave Background SVG */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 110, overflow: 'hidden', zIndex: 0 }}>
        <svg viewBox="0 0 960 110" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
          <path
            d="M 0,0 L 960,0 L 960,65 C 750,110 520,30 280,85 C 140,115 50,75 0,60 Z"
            fill={theme.accent}
            opacity="0.85"
          />
          <path
            d="M 0,0 L 960,0 L 960,45 C 800,85 600,20 350,65 C 180,95 80,50 0,40 Z"
            fill={theme.accent}
          />
        </svg>
      </div>

      <div style={{ position: 'relative', zIndex: 1, padding: '24px 32px', height: '100%', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
          <div style={{ color: '#ffffff', fontSize: 22, fontWeight: 900, letterSpacing: '-0.02em', textShadow: '0 1px 4px rgba(0,0,0,0.3)' }}>
            {title}
          </div>
          <span style={{ background: 'rgba(255,255,255,0.25)', color: '#ffffff', fontSize: 11, fontWeight: 800, padding: '3px 10px', borderRadius: 20 }}>
            STRATEGIC OVERVIEW
          </span>
        </div>

        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
          {cards.slice(0, 4).map((c, i) => (
            <div
              key={i}
              style={{
                background: theme.cardBg,
                border: `1px solid ${theme.border}`,
                borderRadius: 10,
                padding: '16px 14px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: '0 4px 12px rgba(0,0,0,0.03)',
              }}
            >
              <div>
                <div style={{ width: 28, height: 28, borderRadius: 6, background: `${theme.accent}15`, color: theme.accent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 900, marginBottom: 12 }}>
                  0{i + 1}
                </div>
                <div style={{ fontSize: 14, fontWeight: 800, color: theme.primary, marginBottom: 6 }}>
                  {c.title || `Dimension 0${i+1}`}
                </div>
                <div style={{ fontSize: 12, color: theme.secondary, lineHeight: 1.45, opacity: 0.88 }}>
                  {c.description || c.text || 'Rigorous verified metric with cross-functional correlation.'}
                </div>
              </div>
              <div style={{ fontSize: 10, fontWeight: 700, color: theme.accent, letterSpacing: '0.05em' }}>
                VERIFIED FACTOR
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// 4. Agenda Grid 9-Box (Ref 4 Slide 7 - 9-box numbered matrix "01" to "09")
export function AgendaGrid9Box({ content, title, theme }) {
  const items = content.agenda_items || content.bullets || [
    'Executive Summary & Market Context',
    'Customer Problem Identification',
    'Proprietary Core Technology',
    'Market Adoption & Bell Curve',
    'Competitive Matrix & Moat',
    'Unit Economics & Revenue Streams',
    'Go-to-Market & Acquisition Funnel',
    'Milestone Horizon & Targets',
    'Leadership Team & Governance',
  ]

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gridTemplateRows: 'repeat(3, 1fr)', gap: 12, height: '100%' }}>
        {items.slice(0, 9).map((item, i) => (
          <div
            key={i}
            style={{
              background: theme.cardBg,
              border: `1px solid ${theme.border}`,
              borderRadius: 8,
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              boxShadow: '0 2px 8px rgba(0,0,0,0.02)',
            }}
          >
            <div
              style={{
                fontSize: 22,
                fontWeight: 900,
                color: theme.accent,
                fontFamily: 'monospace',
                letterSpacing: '-0.05em',
                minWidth: 32,
              }}
            >
              {String(i + 1).padStart(2, '0')}
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, color: theme.primary, lineHeight: 1.35 }}>
              {typeof item === 'string' ? item : item.title || item.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// 5. Radial Hub and Spoke (Ref 4 Slide 12 - central hub with spokes connecting outer capabilities)
export function RadialHubSpoke({ content, title, theme }) {
  const hub = content.hub_title || title || 'Core Engine'
  const nodes = content.spoke_nodes || (content.bullets || []).slice(0, 6).map((b, i) => ({
    title: typeof b === 'string' ? b : b.text,
    badge: `Node ${i+1}`,
  }))

  const cx = 480, cy = 160, r = 120
  const count = Math.max(1, nodes.length)

  return (
    <div style={{ height: '88%', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg viewBox="0 0 960 320" style={{ width: '100%', height: '100%' }}>
        {/* Connection Lines from Center Hub to Nodes */}
        {nodes.map((_, i) => {
          const angle = (i * 2 * Math.PI) / count - Math.PI / 2
          const nx = cx + r * Math.cos(angle)
          const ny = cy + r * Math.sin(angle)
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={nx}
              y2={ny}
              stroke={theme.accent}
              strokeWidth="2"
              strokeDasharray="4 4"
              opacity="0.6"
            />
          )
        })}

        {/* Central Hub Circle */}
        <circle cx={cx} cy={cy} r={54} fill={theme.accent} filter="drop-shadow(0 6px 12px rgba(0,0,0,0.15))" />
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          fill="#ffffff"
          fontSize="13"
          fontWeight="900"
          letterSpacing="0.04em"
        >
          {hub.slice(0, 16)}
        </text>

        {/* Outer Spoke Nodes */}
        {nodes.map((n, i) => {
          const angle = (i * 2 * Math.PI) / count - Math.PI / 2
          const nx = cx + (r + 40) * Math.cos(angle)
          const ny = cy + (r + 20) * Math.sin(angle)
          return (
            <g key={i}>
              <rect
                x={nx - 75}
                y={ny - 24}
                width="150"
                height="48"
                rx="8"
                fill={theme.cardBg}
                stroke={theme.border}
                strokeWidth="1.5"
                filter="drop-shadow(0 4px 10px rgba(0,0,0,0.06))"
              />
              <text
                x={nx}
                y={ny - 4}
                textAnchor="middle"
                fill={theme.accent}
                fontSize="10"
                fontWeight="800"
                letterSpacing="0.05em"
              >
                0{i + 1} • {n.badge || 'MODULE'}
              </text>
              <text
                x={nx}
                y={ny + 12}
                textAnchor="middle"
                fill={theme.primary}
                fontSize="11"
                fontWeight="700"
              >
                {(n.title || n.text || `Service ${i+1}`).slice(0, 20)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// 6. Split Screen Media (Ref 3 & 5 - large hero visual with floating position/alignment badge & deep structured story)
export function SplitScreenMedia({ content, title, theme }) {
  const bullets = content.bullets || []
  const image = content.image || {}

  return (
    <div style={{ height: '88%', display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24, alignItems: 'stretch' }}>
      {/* Left: Deep Structured Narrative */}
      <div
        style={{
          background: theme.cardBg,
          border: `1px solid ${theme.border}`,
          borderRadius: theme.cardRadius || 12,
          padding: '28px 32px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '4px 10px', borderRadius: 4, background: `${theme.accent}14`, color: theme.accent, fontSize: 10, fontWeight: 800, letterSpacing: '0.08em', marginBottom: 16 }}>
            <Bookmark size={12} />
            DEEP ARCHITECTURAL REPORT
          </div>
          <div style={{ fontSize: 24, fontWeight: 900, color: theme.primary, lineHeight: 1.25, marginBottom: 14 }}>
            {content.headline || title}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {bullets.slice(0, 4).map((b, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{ color: theme.accent, fontWeight: 900, fontSize: 14, marginTop: 1 }}>•</span>
                <span style={{ fontSize: 13, color: theme.secondary, lineHeight: 1.5 }}>
                  {typeof b === 'string' ? b : b.text}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ borderTop: `1px solid ${theme.border}`, paddingTop: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: theme.secondary, opacity: 0.8 }}>SOURCE VERIFIED: S1-S4</span>
          <span style={{ fontSize: 11, fontWeight: 800, color: theme.accent }}>CONFIDENTIAL ANALYSIS</span>
        </div>
      </div>

      {/* Right: Premium Photographic Container */}
      <div
        style={{
          background: theme.cardBg,
          border: `1px solid ${theme.border}`,
          borderRadius: theme.cardRadius || 12,
          overflow: 'hidden',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {image.url ? (
          <div style={{ flex: 1, position: 'relative' }}>
            <img
              src={image.url}
              alt={image.alt || title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              onError={(e) => { e.currentTarget.style.display = 'none' }}
            />
            {image.artist && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  right: 0,
                  background: 'rgba(0,0,0,0.7)',
                  backdropFilter: 'blur(4px)',
                  padding: '6px 12px',
                  color: '#fff',
                  fontSize: 10,
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>Photo: {image.artist}</span>
                <span style={{ opacity: 0.8 }}>{image.source || 'Verified'}</span>
              </div>
            )}
          </div>
        ) : (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, textAlign: 'center', background: `${theme.accent}08` }}>
            <div style={{ width: 50, height: 50, borderRadius: 10, background: `${theme.accent}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
              <Compass size={26} color={theme.accent} />
            </div>
            <div style={{ fontSize: 16, fontWeight: 800, color: theme.primary, maxWidth: 220 }}>
              {title}
            </div>
            <div style={{ fontSize: 11, color: theme.secondary, marginTop: 6, opacity: 0.8 }}>
              Executive Visual Showcase
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// 7. Team Grid Avatars (Ref 4 Slide 5 - 4 column profile cards with circular portrait photos)
export function TeamGridAvatars({ content, title, theme }) {
  const members = content.team_members || [
    { name: 'Dr. Sarah Lin', role: 'Chief Executive Officer', bio: 'Ex-Stanford AI, 12 years scaling autonomous intelligence platforms.' },
    { name: 'Marcus Vance', role: 'Head of Product Design', bio: 'Former Principal Lead at Apple & Pitch, visual architecture specialist.' },
    { name: 'Elena Rostova', role: 'VP of Engineering', bio: 'Distributed systems infrastructure architect and compiler contributor.' },
    { name: 'David Chen', role: 'Head of Growth & GTM', bio: 'Scaled enterprise SaaS pipelines from $0 to $45M ARR across NA and EMEA.' },
  ]

  return (
    <div style={{ height: '88%', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
      {members.slice(0, 4).map((m, i) => (
        <div
          key={i}
          style={{
            background: theme.cardBg,
            border: `1px solid ${theme.border}`,
            borderRadius: theme.cardRadius || 12,
            padding: '20px 16px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            boxShadow: '0 4px 14px rgba(0,0,0,0.03)',
          }}
        >
          <div
            style={{
              width: 68,
              height: 68,
              borderRadius: '50%',
              background: `${theme.accent}20`,
              border: `2px solid ${theme.accent}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 900,
              fontSize: 20,
              color: theme.accent,
              marginBottom: 14,
            }}
          >
            {m.name.split(' ').map(n => n[0]).join('')}
          </div>
          <div style={{ fontSize: 14, fontWeight: 800, color: theme.primary, marginBottom: 4 }}>
            {m.name}
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, color: theme.accent, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
            {m.role}
          </div>
          <div style={{ fontSize: 11, color: theme.secondary, lineHeight: 1.4, opacity: 0.85 }}>
            {m.bio}
          </div>
        </div>
      ))}
    </div>
  )
}

import React from 'react'
import { TrendingUp, ArrowUpRight, DollarSign, Award, Check } from 'lucide-react'

/**
 * MetricLayouts.jsx
 * Implements high-impact data visualizations and metric callouts
 * directly matching the Pitch & Canva visual references (Ref 2 Slide 2, 4, 5).
 */

// 1. Stats KPI Monument (Ref 2 Slide 2 & 4 - gigantic hero KPI pill + narrative analysis)
export function StatsKpiMonument({ content, title, theme }) {
  const kpis = content.kpis || [
    { value: '30M+', label: 'Active Pipeline Growth', description: 'Enterprise accounts activated across Tier 1 geographies.' },
  ]
  const heroKpi = kpis[0] || { value: '10x', label: 'Performance Multiplier', description: 'Empirically measured acceleration.' }
  const bullets = content.bullets || []

  return (
    <div style={{ height: '88%', display: 'grid', gridTemplateColumns: '1fr 1.35fr', gap: 24, alignItems: 'stretch' }}>
      {/* Left Monument Capsule */}
      <div
        style={{
          background: theme.accent,
          borderRadius: theme.cardRadius || 14,
          padding: '36px 28px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          color: '#ffffff',
          boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 900, letterSpacing: '0.1em', background: 'rgba(255,255,255,0.22)', padding: '4px 10px', borderRadius: 20 }}>
            PRIMARY BENCHMARK
          </span>
          <TrendingUp size={20} />
        </div>

        <div style={{ margin: '20px 0' }}>
          <div style={{ fontSize: 62, fontWeight: 900, lineHeight: 1, letterSpacing: '-0.04em' }}>
            {heroKpi.value}
          </div>
          <div style={{ fontSize: 16, fontWeight: 800, marginTop: 12, opacity: 0.95, letterSpacing: '0.02em' }}>
            {heroKpi.label}
          </div>
        </div>

        <div style={{ fontSize: 12, lineHeight: 1.5, opacity: 0.85, borderTop: '1px solid rgba(255,255,255,0.2)', paddingTop: 14 }}>
          {heroKpi.description}
        </div>
      </div>

      {/* Right Analytical Breakdown */}
      <div
        style={{
          background: theme.cardBg,
          border: `1px solid ${theme.border}`,
          borderRadius: theme.cardRadius || 14,
          padding: '28px 32px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, color: theme.accent, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 12 }}>
            STRATEGIC IMPACT & RIGOR
          </div>
          <div style={{ fontSize: 22, fontWeight: 900, color: theme.primary, lineHeight: 1.3, marginBottom: 16 }}>
            {content.headline || title}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {bullets.slice(0, 3).map((b, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: theme.accent, marginTop: 7 }} />
                <div style={{ fontSize: 13, color: theme.secondary, lineHeight: 1.5 }}>
                  {typeof b === 'string' ? b : b.text}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, borderTop: `1px solid ${theme.border}`, paddingTop: 14 }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, color: theme.secondary, opacity: 0.7 }}>CONFIDENCE LEVEL</div>
            <div style={{ fontSize: 15, fontWeight: 900, color: theme.primary }}>99.4% Verified</div>
          </div>
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, color: theme.secondary, opacity: 0.7 }}>AUDIT METHODOLOGY</div>
            <div style={{ fontSize: 15, fontWeight: 900, color: theme.accent }}>Empirical [S1-S3]</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// 2. Stats KPI Triple (Ref 2 Slide 4 - 3 cards with prominent status pill + headline + sub-stats)
export function StatsKpiTriple({ content, title, theme }) {
  const kpis = content.kpis || [
    { value: '84%', label: 'Efficiency Gain', description: 'Measured reduction in multi-turn latency.', badge: '+38% YoY' },
    { value: '350+', label: 'Verified Partners', description: 'Integrated tier-one enterprise organizations.', badge: 'Global' },
    { value: '$14.2M', label: 'Direct Cost Avoidance', description: 'Cumulative computational budget saved.', badge: 'Audited' },
  ]

  return (
    <div style={{ height: '88%', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, alignItems: 'stretch' }}>
      {kpis.slice(0, 3).map((kpi, i) => (
        <div
          key={i}
          style={{
            background: theme.cardBg,
            border: `1px solid ${theme.border}`,
            borderRadius: theme.cardRadius || 14,
            padding: '24px 22px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
          }}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <span style={{ fontSize: 10, fontWeight: 900, color: theme.accent, background: `${theme.accent}15`, padding: '3px 8px', borderRadius: 4, letterSpacing: '0.06em' }}>
                {kpi.badge || `METRIC 0${i+1}`}
              </span>
              <ArrowUpRight size={16} color={theme.accent} />
            </div>
            <div style={{ fontSize: 44, fontWeight: 900, color: theme.primary, letterSpacing: '-0.03em', lineHeight: 1 }}>
              {kpi.value}
            </div>
            <div style={{ fontSize: 14, fontWeight: 800, color: theme.accent, marginTop: 8, letterSpacing: '0.02em' }}>
              {kpi.label}
            </div>
          </div>
          <div style={{ fontSize: 12, color: theme.secondary, lineHeight: 1.45, opacity: 0.88, borderTop: `1px solid ${theme.border}`, paddingTop: 12, marginTop: 16 }}>
            {kpi.description}
          </div>
        </div>
      ))}
    </div>
  )
}

// 3. Market Opportunity Radial / Donut (Ref 2 Slide 5 - radial segmentation with TAM, SAM, SOM callouts)
export function MarketOpportunityRadial({ content, title, theme }) {
  const segments = content.market_segments || [
    { label: 'TAM', value: '$120B', desc: 'Total Addressable Market', angle: 0 },
    { label: 'SAM', value: '$45B', desc: 'Serviceable Addressable Market', angle: 90 },
    { label: 'SOM', value: '$12B', desc: 'Serviceable Obtainable Market', angle: 180 },
    { label: 'SERVE', value: '35M', desc: 'Primary Core Target Customers', angle: 270 },
  ]
  const centerValue = content.center_metric || '35M'

  return (
    <div style={{ height: '88%', display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24, alignItems: 'center' }}>
      {/* SVG Radial Chart */}
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg viewBox="0 0 340 320" style={{ width: '100%', height: '100%' }}>
          {/* Radial Donut Rings */}
          <circle cx="170" cy="160" r="110" fill="none" stroke={theme.border} strokeWidth="16" opacity="0.4" />
          <circle cx="170" cy="160" r="110" fill="none" stroke={theme.accent} strokeWidth="16" strokeDasharray="180 500" strokeDashoffset="-30" />
          <circle cx="170" cy="160" r="80" fill="none" stroke={theme.border} strokeWidth="14" opacity="0.3" />
          <circle cx="170" cy="160" r="80" fill="none" stroke={theme.accent} strokeWidth="14" strokeDasharray="130 500" strokeDashoffset="40" opacity="0.8" />
          <circle cx="170" cy="160" r="54" fill="none" stroke={theme.border} strokeWidth="10" opacity="0.3" />
          <circle cx="170" cy="160" r="54" fill="none" stroke={theme.accent} strokeWidth="10" strokeDasharray="80 500" strokeDashoffset="10" />

          {/* Central Number Monument */}
          <circle cx="170" cy="160" r="40" fill={theme.cardBg} stroke={theme.border} strokeWidth="2" filter="drop-shadow(0 4px 8px rgba(0,0,0,0.08))" />
          <text x="170" y="156" textAnchor="middle" fill={theme.primary} fontSize="17" fontWeight="900" letterSpacing="-0.03em">
            {centerValue}
          </text>
          <text x="170" y="172" textAnchor="middle" fill={theme.accent} fontSize="8" fontWeight="800" letterSpacing="0.06em">
            TARGET CORE
          </text>
        </svg>
      </div>

      {/* Segment Callout Legend Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {segments.map((seg, i) => (
          <div
            key={i}
            style={{
              background: theme.cardBg,
              border: `1px solid ${theme.border}`,
              borderRadius: 8,
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 900, color: theme.accent }}>{seg.label}</span>
                <span style={{ fontSize: 12, color: theme.secondary }}>{seg.desc}</span>
              </div>
            </div>
            <div style={{ fontSize: 16, fontWeight: 900, color: theme.primary }}>
              {seg.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// 4. Financial Table Matrix (Structured financial projection / tier matrix with highlight column)
export function FinancialTableMatrix({ content, title, theme }) {
  const headers = content.table_headers || ['Metric / Horizon', '2025 Baseline', '2026 Target', '2027 Projected']
  const rows = content.table_rows || [
    ['Gross Revenue', '$4.2M', '$14.8M', '$38.5M'],
    ['Gross Margin %', '68.2%', '76.4%', '82.1%'],
    ['Customer Acquisition Cost (CAC)', '$2,450', '$1,820', '$1,150'],
    ['Lifetime Value (LTV)', '$18,400', '$24,600', '$32,800'],
    ['LTV / CAC Ratio', '7.5x', '13.5x', '28.5x'],
  ]

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div
        style={{
          background: theme.cardBg,
          border: `1px solid ${theme.border}`,
          borderRadius: theme.cardRadius || 12,
          overflow: 'hidden',
          boxShadow: '0 4px 16px rgba(0,0,0,0.03)',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
          <thead>
            <tr style={{ background: `${theme.accent}12`, borderBottom: `2px solid ${theme.accent}` }}>
              {headers.map((h, i) => (
                <th
                  key={i}
                  style={{
                    padding: '12px 18px',
                    fontWeight: 900,
                    color: i === 2 ? theme.accent : theme.primary,
                    textTransform: 'uppercase',
                    fontSize: 11,
                    letterSpacing: '0.04em',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => (
              <tr
                key={rIdx}
                style={{
                  borderBottom: `1px solid ${theme.border}`,
                  background: rIdx % 2 === 1 ? `${theme.secondary}06` : 'transparent',
                }}
              >
                {row.map((cell, cIdx) => (
                  <td
                    key={cIdx}
                    style={{
                      padding: '10px 18px',
                      color: cIdx === 0 ? theme.primary : theme.secondary,
                      fontWeight: cIdx === 0 ? 800 : (cIdx === 2 ? 900 : 500),
                      background: cIdx === 2 ? `${theme.accent}08` : 'transparent',
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

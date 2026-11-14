import React from 'react'
import { Server, Database, Cpu, Layers, Check, X, ArrowRight, ShieldCheck, Zap } from 'lucide-react'

/**
 * TechnicalLayouts.jsx
 * Technical architectures, comparison matrices, and multi-step execution flows.
 */

// 1. Technical Architecture Flow (Multi-tier architectural stack)
export function TechnicalArchitectureFlow({ content, title, theme }) {
  const tiers = content.architecture_tiers || [
    { name: 'Edge Presentation & Client Layer', tech: 'React 18 • Widescreen Canvas • WebSocket Streaming', icon: 'Layers' },
    { name: 'API Gateway & Security Layer', tech: 'Reverse Proxy • JWT / OAuth 2.0 • Rate Limiting & Audit', icon: 'Server' },
    { name: 'Agentic Orchestration Engine', tech: 'Gemini Tool Pipeline • Multi-step Synthesis • State Graph', icon: 'Cpu' },
    { name: 'Knowledge & Vector Retrieval (RAG)', tech: 'ChromaDB • Chunking • Semantic Similarity Re-ranking', icon: 'Database' },
    { name: 'Persistent Storage & Export Engine', tech: 'PostgreSQL • Python-PPTX Native Engine • Google Slides API', icon: 'Database' },
  ]

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%', justifyContent: 'center' }}>
        {tiers.map((tier, i) => (
          <div
            key={i}
            style={{
              background: theme.cardBg,
              border: `1px solid ${theme.border}`,
              borderLeft: `4px solid ${theme.accent}`,
              borderRadius: 8,
              padding: '10px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: `${theme.accent}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: theme.accent, fontWeight: 900, fontSize: 11 }}>
                0{i + 1}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800, color: theme.primary }}>
                  {tier.name}
                </div>
                <div style={{ fontSize: 11, color: theme.secondary, opacity: 0.85 }}>
                  {tier.tech}
                </div>
              </div>
            </div>
            <div style={{ fontSize: 10, fontWeight: 800, color: theme.accent, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              TIER 0{i + 1} ACTIVE
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// 2. Comparison Table (Feature-by-feature matrix with checkmarks and metric ratings)
export function ComparisonTable({ content, title, theme }) {
  const headers = content.table_headers || ['Capability / Feature', 'SlideMind AI (Modern)', 'Legacy Slide Tools', 'Generic LLM Output']
  const rows = content.table_rows || [
    ['Authentic 16:9 Design Systems', '✓ 15 Families', '✕ Monolithic Templates', '✕ Plain Text Bullets'],
    ['High-Density Deep Content', '✓ Multi-source RAG', '✕ Manual Typing', '✕ Hallucinated Filler'],
    ['PPTX Vector & Shape Parity', '✓ Native XML Shapes', '✓ Basic Shapes', '✕ No Export'],
    ['Google Slides API Integration', '✓ Live Batch Update', '✕ Broken Formatting', '✕ Unsupported'],
    ['Automated Quality Repair', '✓ Vision Inspector', '✕ None', '✕ None'],
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
                    color: i === 1 ? theme.accent : theme.primary,
                    textTransform: 'uppercase',
                    fontSize: 11,
                    letterSpacing: '0.04em',
                    background: i === 1 ? `${theme.accent}18` : 'transparent',
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
                  background: rIdx % 2 === 1 ? `${theme.secondary}05` : 'transparent',
                }}
              >
                {row.map((cell, cIdx) => {
                  const isCheck = String(cell).startsWith('✓')
                  const isCross = String(cell).startsWith('✕')
                  return (
                    <td
                      key={cIdx}
                      style={{
                        padding: '10px 18px',
                        color: cIdx === 1 ? theme.accent : theme.secondary,
                        fontWeight: cIdx === 1 ? 800 : (cIdx === 0 ? 700 : 500),
                        background: cIdx === 1 ? `${theme.accent}08` : 'transparent',
                      }}
                    >
                      {cell}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// 3. Horizontal Process 4-Step (Ref 1 Slide 7 & Ref 4 Slide 10)
export function HorizontalProcess4Step({ content, title, theme }) {
  const steps = content.process_steps || [
    { title: 'Discovery & RAG', desc: 'Ingest enterprise documentation, whitepapers, and vector embeddings.' },
    { title: 'Narrative Framing', desc: 'Synthesize audience profile and deep storyline architecture.' },
    { title: 'Composition Matching', desc: 'Select authentic design system and structurally unique layouts.' },
    { title: 'Vision Verification', desc: 'Automated contrast, typography, and layout inspection before export.' },
  ]

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        {steps.slice(0, 4).map((st, i) => (
          <div
            key={i}
            style={{
              background: theme.cardBg,
              border: `1px solid ${theme.border}`,
              borderRadius: theme.cardRadius || 10,
              padding: '18px 16px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              position: 'relative',
              boxShadow: '0 4px 12px rgba(0,0,0,0.03)',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 6,
                    background: theme.accent,
                    color: '#ffffff',
                    fontWeight: 900,
                    fontSize: 14,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {i + 1}
                </div>
                {i < 3 && <ArrowRight size={14} color={theme.accent} opacity={0.6} />}
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, color: theme.primary, marginBottom: 8, lineHeight: 1.3 }}>
                {st.title}
              </div>
              <div style={{ fontSize: 11, color: theme.secondary, lineHeight: 1.45, opacity: 0.88 }}>
                {st.desc || st.description || 'Systematic execution vector verified under enterprise constraints.'}
              </div>
            </div>
            <div style={{ marginTop: 14, fontSize: 9, fontWeight: 800, color: theme.accent, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              STAGE 0{i + 1} COMPLETE
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// 4. SWOT Analysis Matrix (2x2 Grid)
export function SwotAnalysisMatrix({ content, title, theme }) {
  const quadrants = [
    { title: 'Strengths', badge: 'INTERNAL • POSITIVE', color: '#10b981', points: content.swot?.strengths || ['Proprietary Multimodal Engine', 'Enterprise RAG Accuracy', 'Sub-second PPTX Rendering'] },
    { title: 'Weaknesses', badge: 'INTERNAL • FRICTION', color: '#f59e0b', points: content.swot?.weaknesses || ['API Concurrency Limits', 'Initial Cold Start Overheads', 'Complex Theme Discovery'] },
    { title: 'Opportunities', badge: 'EXTERNAL • GROWTH', color: '#3b82f6', points: content.swot?.opportunities || ['Enterprise Team Workspaces', 'Automated Brand Kit Sync', 'Multi-Language Localization'] },
    { title: 'Threats', badge: 'EXTERNAL • RISK', color: '#ef4444', points: content.swot?.threats || ['Rapidly Shifting LLM API Pricing', 'Legacy Monolithic Incumbents', 'Formatting Drift on Export'] },
  ]

  return (
    <div style={{ height: '88%', display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: 14 }}>
      {quadrants.map((q, i) => (
        <div
          key={i}
          style={{
            background: theme.cardBg,
            border: `1px solid ${theme.border}`,
            borderTop: `4px solid ${q.color}`,
            borderRadius: 8,
            padding: '14px 18px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 900, color: theme.primary }}>{q.title}</span>
            <span style={{ fontSize: 9, fontWeight: 800, color: q.color, letterSpacing: '0.06em' }}>{q.badge}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1, justifyContent: 'center' }}>
            {q.points.slice(0, 3).map((pt, pIdx) => (
              <div key={pIdx} style={{ fontSize: 11, color: theme.secondary, display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ color: q.color, fontWeight: 900 }}>•</span>
                <span>{typeof pt === 'string' ? pt : pt.text}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

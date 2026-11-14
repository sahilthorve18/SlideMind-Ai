import React from 'react'
import {
  QrCode,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  Wrench,
  UserCheck,
  FileText,
  Activity,
  Layers,
} from 'lucide-react'

/**
 * OperationalLayouts.jsx
 * Specialized layout components for operational software, ticketing systems,
 * service management, technician workflows, and administrative monitoring dashboards.
 */

// 1. Ticket Lifecycle Flow (Sequential Step-by-Step Resolution Process)
export function TicketLifecycleFlow({ content, title, theme }) {
  const steps = content.process_steps || [
    { title: 'Incident Logged', description: 'Student or faculty scans room QR code or submits mobile incident form.' },
    { title: 'Automated Ticket ID', description: 'System assigns priority SLA, tags facility equipment, and alerts on-duty team.' },
    { title: 'Technician Dispatched', description: 'Assigned specialist inspects equipment, replaces parts, and logs resolution.' },
    { title: 'User Confirmation', description: 'Original reporter tests fix and provides explicit digital sign-off verification.' },
  ]

  const statusIcons = [QrCode, AlertCircle, Wrench, UserCheck, ShieldCheck]

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(steps.length, 4)}, 1fr)`, gap: 14 }}>
        {steps.slice(0, 4).map((st, i) => {
          const IconComp = statusIcons[i % statusIcons.length]
          return (
            <div
              key={i}
              style={{
                background: theme.cardBg,
                border: `1px solid ${theme.border}`,
                borderRadius: theme.cardRadius || 10,
                padding: '20px 18px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                position: 'relative',
                boxShadow: '0 4px 14px rgba(0,0,0,0.04)',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 8,
                      background: `${theme.accent}18`,
                      color: theme.accent,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <IconComp size={18} />
                  </div>
                  {i < Math.min(steps.length, 4) - 1 && (
                    <ArrowRight size={15} color={theme.accent} opacity={0.6} />
                  )}
                </div>

                <div style={{ fontSize: 11, fontWeight: 800, color: theme.accent, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4 }}>
                  STAGE 0{st.step_number || i + 1}
                </div>

                <div style={{ fontSize: 15, fontWeight: 800, color: theme.primary, marginBottom: 8, lineHeight: 1.3 }}>
                  {st.title}
                </div>

                <div style={{ fontSize: 12, color: theme.secondary, lineHeight: 1.5, opacity: 0.9 }}>
                  {st.description}
                </div>
              </div>

              <div
                style={{
                  marginTop: 14,
                  paddingTop: 10,
                  borderTop: `1px dashed ${theme.border}`,
                  fontSize: 10,
                  fontWeight: 700,
                  color: theme.accent,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <CheckCircle2 size={11} /> SLA ENFORCED
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// 2. Feature Showcase & Record Keeping Cards
export function FeatureShowcase({ content, title, theme }) {
  const cards = content.cards || [
    { title: 'Digital Asset Tagging', badge: 'RECORD 01', description: 'Every campus facility asset (fans, lighting, projectors) is mapped with unique QR IDs.' },
    { title: 'Automated Routing', badge: 'DISPATCH 02', description: 'System dynamically assigns priority queues based on building zone, severity, and trade.' },
    { title: 'Verified Resolution', badge: 'AUDIT 03', description: 'Tickets remain active until the submitting user confirms successful fix in-app.' },
  ]

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(cards.length, 3)}, 1fr)`, gap: 16 }}>
        {cards.slice(0, 3).map((cd, i) => (
          <div
            key={i}
            style={{
              background: theme.cardBg,
              border: `1px solid ${theme.border}`,
              borderTop: `4px solid ${theme.accent}`,
              borderRadius: theme.cardRadius || 10,
              padding: '24px 20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 4px 14px rgba(0,0,0,0.03)',
            }}
          >
            <div>
              <div
                style={{
                  display: 'inline-block',
                  background: `${theme.accent}15`,
                  color: theme.accent,
                  fontSize: 10,
                  fontWeight: 800,
                  padding: '3px 9px',
                  borderRadius: 4,
                  marginBottom: 14,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}
              >
                {cd.badge || `CAPABILITY 0${i + 1}`}
              </div>

              <div style={{ fontSize: 17, fontWeight: 800, color: theme.primary, marginBottom: 10, lineHeight: 1.3 }}>
                {cd.title}
              </div>

              <div style={{ fontSize: 13, color: theme.secondary, lineHeight: 1.6, opacity: 0.9 }}>
                {cd.description || cd.body}
              </div>
            </div>

            <div
              style={{
                marginTop: 18,
                paddingTop: 12,
                borderTop: `1px solid ${theme.border}`,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 11,
                fontWeight: 700,
                color: theme.primary,
              }}
            >
              <FileText size={13} color={theme.accent} />
              <span>Standard Operating Protocol</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// 3. Operational Monitoring & Admin Oversight Dashboard
export function OperationalDashboard({ content, title, theme }) {
  const kpis = content.kpis || [
    { value: 'Active', label: 'System Queue Health', description: 'Real-time incident ticket intake and automated classification.' },
    { value: 'Verified', label: 'User Sign-off Rule', description: 'Zero unverified closures; student approval required to resolve.' },
    { value: '100%', label: 'Audit Trail Coverage', description: 'Timestamped logs across reporting, technician dispatch, and completion.' },
  ]

  const bullets = content.bullets || []

  return (
    <div style={{ height: '88%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      {/* 3 Status KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
        {kpis.slice(0, 3).map((kp, i) => (
          <div
            key={i}
            style={{
              background: theme.cardBg,
              border: `1px solid ${theme.border}`,
              borderRadius: theme.cardRadius || 10,
              padding: '18px 18px',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 4px 12px rgba(0,0,0,0.03)',
            }}
          >
            <div style={{ fontSize: 10, fontWeight: 800, color: theme.accent, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>
              {kp.label}
            </div>
            <div style={{ fontSize: 32, fontWeight: 900, color: theme.accent, marginBottom: 6, letterSpacing: '-0.02em' }}>
              {kp.value}
            </div>
            <div style={{ fontSize: 11, color: theme.secondary, lineHeight: 1.4, opacity: 0.85 }}>
              {kp.description}
            </div>
          </div>
        ))}
      </div>

      {/* Admin Monitoring Controls & Protocol Feed */}
      <div
        style={{
          background: theme.cardBg,
          border: `1px solid ${theme.border}`,
          borderRadius: theme.cardRadius || 10,
          padding: '18px 22px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.03)',
          marginTop: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <Activity size={16} color={theme.accent} />
          <span style={{ fontSize: 12, fontWeight: 800, color: theme.primary, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Administrative Control Protocols & Monitoring Highlights
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(bullets.length > 0 ? bullets.slice(0, 3) : [
            { text: 'Campus administrators retain real-time visibility across all open, assigned, and pending tickets.' },
            { text: 'Automated escalation alerts trigger when technician response exceeds target SLA thresholds.' },
            { text: 'Comprehensive maintenance history logs inform future preventative equipment servicing schedules.' },
          ]).map((b, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: theme.accent, marginTop: 6, flexShrink: 0 }} />
              <div style={{ fontSize: 12, color: theme.primary, lineHeight: 1.5 }}>
                {b.text || String(b)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

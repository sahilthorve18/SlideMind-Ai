import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, Line, LineChart, Pie, PieChart, XAxis, YAxis } from 'recharts'

// Draws a layout "scene" produced by the backend solver (backend/services/deck). The same scene is used to
// write the PPTX and PDF, so this preview matches the exported files. All units: 1 inch = 72 px, slide 960x540.
const PX = 72
const FONTS = {
  Calibri: "Calibri, Carlito, 'Segoe UI', Arial, sans-serif",
  Georgia: "Georgia, 'Times New Roman', serif",
  Consolas: "Consolas, 'Courier New', monospace",
}
const hex = (h, a = 1) => {
  if (!h) return 'transparent'
  const n = parseInt(h, 16)
  return a >= 1 ? `#${h}` : `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
}

const KEYFRAMES = `
@keyframes sm-fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes sm-wipe{from{clip-path:inset(0 100% 0 0);opacity:.2}to{clip-path:inset(0 0 0 0);opacity:1}}
@media (prefers-reduced-motion: reduce){.sm-anim{animation:none!important}}
`

function Chart({ p }) {
  const w = p.w * PX
  const h = p.h * PX
  const data = p.labels.map((l, i) => {
    const row = { name: l }
    p.series.forEach((s, j) => {
      row[`s${j}`] = s.values[i]
    })
    return row
  })
  const axis = { fill: `#${p.fg}`, fontSize: 14 }
  if (p.kind === 'pie' || p.kind === 'donut') {
    const d = data.map((r) => ({ name: r.name, value: r.s0 }))
    return (
      <PieChart width={w} height={h}>
        <Pie data={d} dataKey="value" nameKey="name" innerRadius={p.kind === 'donut' ? '50%' : 0} outerRadius="85%" stroke={`#${p.bg}`}
          label={{ fill: `#${p.fg}`, fontSize: 14 }} isAnimationActive={false}>
          {d.map((_, i) => <Cell key={i} fill={`#${p.colors[i % p.colors.length]}`} />)}
        </Pie>
        <Legend layout="vertical" align="right" verticalAlign="middle" wrapperStyle={{ color: `#${p.fg}`, fontSize: 14 }} />
      </PieChart>
    )
  }
  const multi = p.series.length > 1
  if (p.kind === 'line') {
    return (
      <LineChart width={w} height={h} data={data}>
        <CartesianGrid stroke={`#${p.grid}`} vertical={false} />
        <XAxis dataKey="name" tick={axis} stroke={`#${p.grid}`} />
        <YAxis tick={axis} stroke="none" />
        {p.series.map((s, i) => <Line key={i} dataKey={`s${i}`} name={s.name} stroke={`#${p.colors[i % p.colors.length]}`} strokeWidth={3} isAnimationActive={false} />)}
        {multi && <Legend wrapperStyle={{ color: `#${p.fg}`, fontSize: 14 }} />}
      </LineChart>
    )
  }
  return (
    <BarChart width={w} height={h} data={data} layout={p.kind === 'hbar' ? 'vertical' : 'horizontal'}>
      <CartesianGrid stroke={`#${p.grid}`} vertical={false} />
      {p.kind === 'hbar'
        ? (<><XAxis type="number" tick={axis} stroke="none" /><YAxis type="category" dataKey="name" tick={axis} stroke={`#${p.grid}`} /></>)
        : (<><XAxis dataKey="name" tick={axis} stroke={`#${p.grid}`} /><YAxis tick={axis} stroke="none" /></>)}
      {p.series.map((s, i) => (
        <Bar key={i} dataKey={`s${i}`} name={s.name} fill={`#${p.colors[i % p.colors.length]}`} isAnimationActive={false}>
          {!multi && <LabelList dataKey={`s${i}`} position={p.kind === 'hbar' ? 'right' : 'top'} fill={`#${p.fg}`} fontSize={14} />}
        </Bar>
      ))}
      {multi && <Legend wrapperStyle={{ color: `#${p.fg}`, fontSize: 14 }} />}
    </BarChart>
  )
}

function Item({ p }) {
  const base = { position: 'absolute', left: p.x * PX, top: p.y * PX, width: p.w * PX, height: p.h * PX }
  switch (p.k) {
    case 'rect':
    case 'ellipse':
      return (
        <div style={{ ...base, background: p.fill ? hex(p.fill, p.alpha) : 'transparent', border: p.line ? `${p.lw}px solid #${p.line}` : 'none',
          borderRadius: p.k === 'ellipse' ? '50%' : (p.r || 0) * PX, boxSizing: 'border-box' }} />
      )
    case 'text':
      return (
        <div style={{ ...base, display: 'flex', alignItems: { t: 'flex-start', m: 'center', b: 'flex-end' }[p.valign || 't'],
          fontFamily: FONTS[p.font] || FONTS.Calibri, fontSize: p.size, lineHeight: 1.2, fontWeight: p.bold ? 700 : 400,
          fontStyle: p.italic ? 'italic' : 'normal', color: `#${p.color}`, textAlign: { l: 'left', c: 'center', r: 'right' }[p.align || 'l'] }}>
          <div style={{ width: '100%' }}>{p.text}</div>
        </div>
      )
    case 'image': {
      const imgSrc = typeof p.src === 'string' ? p.src : (p.src?.url || p.src?.image_url || '')
      if (!imgSrc) return null
      return (
        <img
          src={imgSrc}
          alt={p.alt || ''}
          style={{
            ...base,
            objectFit: 'cover',
            borderRadius: (p.r || 0) * PX,
            border: p.line ? `1px solid #${p.line}` : 'none',
          }}
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />
      )
    }
    case 'line': {
      const id = `ah${Math.round(p.x1 * 100)}${Math.round(p.y1 * 100)}${Math.round(p.x2 * 100)}${Math.round(p.y2 * 100)}`
      return (
        <svg width="960" height="540" style={{ position: 'absolute', left: 0, top: 0, pointerEvents: 'none', overflow: 'visible' }}>
          {p.arrow && (
            <defs><marker id={id} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill={`#${p.color}`} /></marker></defs>
          )}
          <line x1={p.x1 * PX} y1={p.y1 * PX} x2={p.x2 * PX} y2={p.y2 * PX} stroke={`#${p.color}`} strokeWidth={p.lw}
            strokeDasharray={p.dash ? '6 5' : undefined} markerEnd={p.arrow ? `url(#${id})` : undefined} />
        </svg>
      )
    }
    case 'chart':
      return <div style={base}><Chart p={p} /></div>
    default:
      return null
  }
}

export default function SceneView({ scene, animate = true }) {
  // Items sharing a block group fade/wipe in together; blocks follow one another like the PowerPoint animation.
  const groups = [...new Set(scene.items.filter((i) => i.g >= 1 && i.g < 90).map((i) => i.g))].sort((a, b) => a - b)
  const order = Object.fromEntries(groups.map((g, i) => [g, i]))
  const name = scene.entrance === 'wipe' ? 'sm-wipe' : 'sm-fade'
  return (
    <div style={{ width: 960, height: 540, position: 'relative', background: `#${scene.bg}`, overflow: 'hidden' }}>
      <style>{KEYFRAMES}</style>
      {scene.items.map((p, i) => {
        const animated = animate && p.g >= 1 && p.g < 90
        return (
          <div key={i} className={animated ? 'sm-anim' : undefined}
            style={animated ? { position: 'absolute', inset: 0, animation: `${name} .5s ease-out both`, animationDelay: `${0.25 + order[p.g] * 0.45}s` } : { position: 'absolute', inset: 0 }}>
            <Item p={p} />
          </div>
        )
      })}
    </div>
  )
}

import { useState, useRef } from 'react'
import { Eye, Zap, ArrowRight, Sparkles } from 'lucide-react'

/**
 * ModernTemplateCard: Renders an authentically distinct, highly polished 16:9 visual preview
 * for each individual design system. Includes a luxury 3D interactive spotlight, ambient halo bloom,
 * specular gleam sweep, and floating frosted action capsule on hover.
 */
export default function ModernTemplateCard({ tmpl, onInspect, onUse }) {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, tiltX: 0, tiltY: 0, isHovered: false })
  const cardRef = useRef(null)

  const handleMouseMove = (e) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    // Smooth micro tilt: max 3.5 degrees
    const tiltX = Math.max(-3.5, Math.min(3.5, ((y - centerY) / centerY) * -3.5))
    const tiltY = Math.max(-3.5, Math.min(3.5, ((x - centerX) / centerX) * 3.5))
    setMousePos({ x, y, tiltX, tiltY, isHovered: true })
  }

  const handleMouseLeave = () => {
    setMousePos({ x: 0, y: 0, tiltX: 0, tiltY: 0, isHovered: false })
  }
  // Render bespoke 16:9 canvas per design system
  const renderBespokeCanvas = () => {
    switch (tmpl.id) {
      // 1. Linear Precision: Dark Software IDE Split-Screen
      case 'linear_dark':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3 select-none flex flex-col justify-between overflow-hidden bg-[#09090b] border border-[#27272a] font-sans">
            {/* Top Bar with Status Tag */}
            <div className="flex items-center justify-between border-b border-[#27272a] pb-2">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
                <span className="text-[9px] font-mono font-medium text-zinc-400">CORE // ENG-2026</span>
              </div>
              <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-sky-950/60 border border-sky-500/30 text-sky-400">
                &lt;12ms P99
              </span>
            </div>

            {/* Split Screen Layout */}
            <div className="grid grid-cols-12 gap-2 my-auto items-center">
              <div className="col-span-7 space-y-1">
                <h4 className="text-xs font-bold text-white tracking-tight leading-tight">
                  Next-Gen Neural Execution Engine
                </h4>
                <p className="text-[8px] text-zinc-400 line-clamp-1">
                  Sub-second latency across distributed edge nodes
                </p>
              </div>
              <div className="col-span-5 rounded-md border border-[#27272a] bg-[#121217] p-1.5 space-y-1">
                <div className="flex justify-between text-[7px] font-mono text-zinc-400">
                  <span>THROUGHPUT</span>
                  <span className="text-sky-400 font-bold">4.8X</span>
                </div>
                <div className="w-full bg-zinc-800 h-1 rounded-full overflow-hidden">
                  <div className="bg-sky-500 h-full w-[85%]" />
                </div>
              </div>
            </div>

            {/* Bottom Spec Footer */}
            <div className="flex items-center justify-between text-[8px] font-mono text-zinc-500 pt-1 border-t border-[#27272a]">
              <span>[01/SPEC]</span>
              <span className="text-zinc-400">99.99% UPTIME</span>
            </div>
          </div>
        )

      // 2. Apple Keynote: OLED Pitch-Black with Radiant Azure Glow
      case 'apple_keynote':
        return (
          <div className="relative aspect-video w-full rounded-xl p-4 select-none flex flex-col justify-between items-center text-center overflow-hidden bg-black border border-[#222227]">
            {/* Ambient Optical Azure Radial Glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full bg-sky-500/20 blur-2xl pointer-events-none" />

            <span className="relative z-10 text-[8px] font-semibold tracking-widest text-sky-400 uppercase">
              SPECIAL KEYNOTE BRIEFING
            </span>

            <div className="relative z-10 space-y-1 my-auto">
              <h4 className="text-sm font-extrabold text-white tracking-tight leading-tight">
                Pro Performance. Engineered.
              </h4>
              <p className="text-[9px] text-zinc-400 max-w-[220px] mx-auto opacity-80">
                Zero compromise on speed, fidelity, and silicon efficiency.
              </p>
            </div>

            <div className="relative z-10 flex items-center gap-2 text-[8px] text-zinc-500">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
              <span className="tracking-wider uppercase">M-SERIES COMPUTE</span>
            </div>
          </div>
        )

      // 3. Editorial Monocle: Warm Oat Paper with Serif Italics & Drop-Cap
      case 'editorial_monocle':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3.5 select-none flex flex-col justify-between overflow-hidden bg-[#faf7f2] border border-[#e7ded5] text-[#1c1917]">
            {/* Header Serif Kicker */}
            <div className="flex items-center justify-between border-b border-[#e7ded5] pb-1.5">
              <span className="font-serif italic text-[10px] text-[#c2410c]">
                A Monograph on Strategic Craft —
              </span>
              <span className="font-mono text-[8px] text-[#78716c]">VOL. 08</span>
            </div>

            {/* Editorial Spread */}
            <div className="my-auto space-y-1">
              <h4 className="font-serif font-bold text-xs text-[#1c1917] leading-snug">
                The Architecture of Quiet Thought & Autonomy
              </h4>
              <p className="font-serif italic text-[9px] text-[#57534e] line-clamp-2">
                “Essays on creative autonomy, intellectual rigor, and humane technology.”
              </p>
            </div>

            {/* Terracotta Hairline & Footer */}
            <div className="flex items-center justify-between border-t border-[#c2410c]/30 pt-1 text-[8px] text-[#78716c]">
              <span>ESSAY NO. 04</span>
              <span className="font-serif italic text-[#c2410c]">Monocle Direction</span>
            </div>
          </div>
        )

      // 4. Neo-Brutalist Raw: 2px Borders, 0px Radius, Safety Orange
      case 'brutalist_raw':
        return (
          <div className="relative aspect-video w-full p-2.5 select-none flex flex-col justify-between overflow-hidden bg-white border-2 border-black font-mono">
            {/* Inverted Black Header */}
            <div className="bg-black text-white p-1 flex justify-between items-center">
              <span className="bg-[#f97316] text-black font-black text-[8px] px-1">
                // SPEC_01
              </span>
              <span className="text-[8px] font-bold">RAW_ARCH</span>
            </div>

            {/* Massive Aggressive Title */}
            <div className="my-auto py-1">
              <h4 className="text-xs font-black uppercase text-black tracking-tight leading-none">
                SYSTEM ARCHITECTURE // V4.0
              </h4>
              <p className="text-[8px] text-zinc-600 mt-1 uppercase font-bold">
                0PX RADIUS. PURE MONOSPACE SPECS.
              </p>
            </div>

            {/* Brutalist Grid Boxes */}
            <div className="grid grid-cols-2 gap-1.5 border-t-2 border-black pt-1 text-[7px] font-black">
              <div className="border border-black p-0.5 text-center bg-[#f4f4f5]">
                [01] ZERO FLUFF
              </div>
              <div className="border border-black p-0.5 text-center bg-[#f97316] text-black">
                [02] 100% DISCIPLINE
              </div>
            </div>
          </div>
        )

      // 5. Stripe FinTech: Clean Architectural Slate & Cobalt Metric Cards
      case 'stripe_scale':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3 select-none flex flex-col justify-between overflow-hidden bg-[#f8fafc] border border-[#e2e8f0] font-sans">
            {/* Top Bar with Cobalt Brand Pill */}
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded-full bg-sky-50 border border-sky-200 text-sky-700 text-[8px] font-bold uppercase tracking-wider">
                FinTech Scale
              </span>
              <span className="text-[8px] font-mono text-slate-400">USD // GLOBAL</span>
            </div>

            {/* Headline */}
            <div className="my-auto">
              <h4 className="text-xs font-bold text-slate-900 tracking-tight leading-tight">
                Unified Payment Infrastructure
              </h4>
              <div className="mt-1.5 grid grid-cols-2 gap-1.5">
                <div className="rounded-lg bg-white p-1.5 border border-slate-200 shadow-xs">
                  <div className="text-[7px] text-slate-400 uppercase font-semibold">ARR Volume</div>
                  <div className="text-xs font-black text-slate-900">$4.2B</div>
                </div>
                <div className="rounded-lg bg-white p-1.5 border border-slate-200 shadow-xs">
                  <div className="text-[7px] text-slate-400 uppercase font-semibold">Net Surge</div>
                  <div className="text-xs font-black text-emerald-600">+142% YoY</div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between text-[7px] text-slate-400 pt-1 border-t border-slate-200">
              <span>135+ Currencies</span>
              <span className="text-sky-600 font-semibold">Verified Liquidity</span>
            </div>
          </div>
        )

      // 6. Cyber Terminal: Dark CRT Hacker Window with Code Prompts
      case 'cyber_terminal':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3 select-none flex flex-col justify-between overflow-hidden bg-[#050908] border border-[#143026] font-mono">
            {/* MacOS Style Window Control Dots */}
            <div className="flex items-center justify-between border-b border-[#143026] pb-1.5">
              <div className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500/80" />
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500/80" />
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/80" />
                <span className="text-[8px] text-emerald-400/70 ml-1">root@neural:~$</span>
              </div>
              <span className="text-[7px] text-cyan-400">140M T/S</span>
            </div>

            {/* Terminal Code Execution */}
            <div className="my-auto space-y-1">
              <div className="text-[8px] text-emerald-300">
                &gt; neural_engine.deploy(mesh=distributed)
              </div>
              <h4 className="text-xs font-bold text-white tracking-tight leading-tight">
                Autonomous Reasoning & Mesh
              </h4>
              <div className="text-[8px] text-emerald-400/90 font-semibold">
                [OK] LATENCY 0.42S • ACCURACY 99.8%
              </div>
            </div>

            {/* Telemetry Footer */}
            <div className="flex items-center justify-between text-[7px] text-emerald-600 border-t border-[#143026] pt-1">
              <span>PORT // 8080</span>
              <span className="text-cyan-400 animate-pulse">● STREAMING</span>
            </div>
          </div>
        )

      // 7. Bauhaus 12-Column: Swiss Grid with Giant Red 01 Numeral Anchor
      case 'swiss_bauhaus':
        return (
          <div className="relative aspect-video w-full p-3 select-none flex flex-col justify-between overflow-hidden bg-[#f4f3ef] border border-[#d8d6cc] text-[#09090b] font-sans">
            {/* Top Vermillion Line */}
            <div className="w-full h-1 bg-[#eb3324] mb-1" />

            {/* Asymmetrical Swiss Grid */}
            <div className="grid grid-cols-12 gap-2 my-auto items-center">
              <div className="col-span-4 text-center border-r border-[#d8d6cc] pr-2">
                <span className="text-2xl font-black text-[#eb3324] leading-none block">
                  01
                </span>
                <span className="text-[7px] font-mono text-zinc-500 uppercase tracking-widest">
                  SYSTEM
                </span>
              </div>
              <div className="col-span-8 space-y-1 pl-1">
                <h4 className="text-xs font-black text-[#09090b] tracking-tight leading-tight uppercase">
                  Modernist Systems & Order
                </h4>
                <p className="text-[8px] text-zinc-600 leading-tight">
                  Mathematical grid discipline and objective clarity.
                </p>
              </div>
            </div>

            {/* Swiss Mathematical Footer */}
            <div className="flex items-center justify-between text-[8px] font-mono text-zinc-500 pt-1 border-t border-[#d8d6cc]">
              <span>ZÜRICH 1957</span>
              <span className="text-[#eb3324] font-bold">12-COL MODULAR</span>
            </div>
          </div>
        )

      // 8. Pitch Venture: Deep Graphite with Radioactive Lime Traction
      case 'pitch_venture':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3 select-none flex flex-col justify-between overflow-hidden bg-[#0a0b0e] border border-[#1f2433] font-sans">
            {/* Top Series A Tag */}
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[8px] font-bold uppercase tracking-wider">
                Series A Pitch
              </span>
              <span className="text-[8px] font-mono text-emerald-400 font-bold">+310% NDR</span>
            </div>

            {/* Executive Pitch Hook */}
            <div className="my-auto space-y-1">
              <h4 className="text-xs font-extrabold text-white tracking-tight leading-tight">
                The Operating System for Modern Teams
              </h4>
              <p className="text-[8px] text-zinc-400 line-clamp-1">
                Eliminating enterprise communication friction at scale
              </p>
            </div>

            {/* 3 Metric Pills */}
            <div className="grid grid-cols-3 gap-1 pt-1.5 border-t border-[#1f2433] text-center">
              <div className="rounded bg-white/5 p-1">
                <div className="text-[9px] font-extrabold text-white">$12.4M</div>
                <div className="text-[6px] text-zinc-400">ARR</div>
              </div>
              <div className="rounded bg-white/5 p-1">
                <div className="text-[9px] font-extrabold text-emerald-400">310%</div>
                <div className="text-[6px] text-zinc-400">RETENTION</div>
              </div>
              <div className="rounded bg-white/5 p-1">
                <div className="text-[9px] font-extrabold text-amber-400">18 Mo.</div>
                <div className="text-[6px] text-zinc-400">RUNWAY</div>
              </div>
            </div>
          </div>
        )

      // 9. Luxury Maison: Velvet Noir with Champagne Gold Emblem & Didot
      case 'luxury_maison':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3.5 select-none flex flex-col justify-between items-center text-center overflow-hidden bg-[#0c0c0e] border border-[#2c271b]">
            {/* Gold Emblem */}
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#d4af37]" />
              <span className="text-[8px] tracking-[0.25em] text-[#d4af37] uppercase font-serif">
                MAISON NOIR
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#d4af37]" />
            </div>

            {/* Refined Serif Title */}
            <div className="my-auto space-y-1">
              <h4 className="font-serif text-xs font-normal text-white tracking-[0.08em] uppercase leading-relaxed">
                The Mastery of Mechanical Heritage
              </h4>
              <div className="w-8 h-[1px] bg-[#d4af37]/60 mx-auto my-1" />
              <p className="font-serif italic text-[8px] text-zinc-400">
                Crafting timeless horological complications since 1892
              </p>
            </div>

            {/* Minimal Gold Hairline Footer */}
            <div className="flex items-center justify-between w-full text-[7px] text-zinc-500 font-serif border-t border-[#2c271b] pt-1">
              <span>EDITION NO. 01</span>
              <span className="text-[#d4af37]">0.001MM TOLERANCE</span>
            </div>
          </div>
        )

      // 10. Nordic Frost: Architectural Minimalist Glacier Grid
      case 'nordic_frost':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3 select-none flex flex-col justify-between overflow-hidden bg-[#f2f5f9] border border-[#d5e0ec] font-sans">
            <div className="flex items-center justify-between border-b border-[#d5e0ec] pb-1.5">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#0284c7]" />
                <span className="text-[9px] font-mono font-semibold tracking-wider text-[#0b1a2e]">
                  OSLO // ARCH-01
                </span>
              </div>
              <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-sky-100 text-[#0284c7] font-bold">
                0.4MM TOLERANCE
              </span>
            </div>
            <div className="grid grid-cols-12 gap-2 my-auto items-center">
              <div className="col-span-8 space-y-1">
                <h4 className="text-xs font-bold text-[#0b1a2e] tracking-tight leading-tight">
                  Architectural Precision &amp; Nordic Order
                </h4>
                <p className="text-[8px] text-[#64748b] line-clamp-1">
                  Human-centered spaces designed with deliberate restraint
                </p>
              </div>
              <div className="col-span-4 bg-white border border-[#d5e0ec] rounded p-1.5 text-center shadow-xs">
                <div className="text-[11px] font-extrabold text-[#0284c7]">A++</div>
                <div className="text-[7px] text-[#64748b] uppercase">Efficiency</div>
              </div>
            </div>
            <div className="flex items-center justify-between text-[7px] text-[#64748b] border-t border-[#d5e0ec] pt-1">
              <span>CIRCULAR SPRUCE</span>
              <span className="font-mono text-[#0284c7]">100% TIMBER</span>
            </div>
          </div>
        )

      // 11. Tokyo Neon: Cyberpunk Void with Electric Violet Glow
      case 'tokyo_neon':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3 select-none flex flex-col justify-between overflow-hidden bg-[#080811] border border-[#232042] font-sans">
            <div className="absolute top-0 right-0 w-24 h-24 bg-purple-600/15 rounded-full blur-2xl pointer-events-none" />
            <div className="flex items-center justify-between border-b border-[#232042] pb-1.5 relative z-10">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#a855f7] shadow-[0_0_8px_#a855f7]" />
                <span className="text-[9px] font-mono font-bold text-white tracking-widest">
                  NEO-TOKYO // HUD
                </span>
              </div>
              <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-purple-950/80 border border-purple-500/40 text-[#c084fc] font-bold">
                2.4M TPS
              </span>
            </div>
            <div className="grid grid-cols-12 gap-2 my-auto items-center relative z-10">
              <div className="col-span-7 space-y-1">
                <h4 className="text-xs font-bold text-white tracking-tight leading-tight">
                  Neural Mesh Telemetry &amp; Frontier Models
                </h4>
                <p className="text-[8px] text-zinc-400 line-clamp-1">
                  Sub-second tensor streaming across distributed clusters
                </p>
              </div>
              <div className="col-span-5 bg-[#10101f] border border-[#3b2d66] rounded-lg p-1.5 space-y-0.5">
                <div className="flex justify-between text-[7px] font-mono text-zinc-400">
                  <span>P99</span>
                  <span className="text-[#a855f7]">4.2ms</span>
                </div>
                <div className="w-full bg-[#1e1b38] h-1 rounded-full overflow-hidden">
                  <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-full w-[88%]" />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between text-[7px] text-zinc-500 font-mono border-t border-[#232042] pt-1 relative z-10">
              <span>DECENTRALIZED NODE</span>
              <span className="text-[#ec4899]">99.98% VERIFIED</span>
            </div>
          </div>
        )

      // 12. California Warmth: Sun-Drenched Oat & Sunset Terracotta
      case 'california_warmth':
        return (
          <div className="relative aspect-video w-full rounded-xl p-3 select-none flex flex-col justify-between overflow-hidden bg-[#fbf8f3] border border-[#eedfcb] font-sans">
            <div className="flex items-center justify-between border-b border-[#eedfcb] pb-1.5">
              <span className="px-2 py-0.5 rounded-full bg-[#d9532f]/10 border border-[#d9532f]/30 text-[#d9532f] text-[8px] font-bold tracking-wider uppercase">
                PACIFIC STUDIO
              </span>
              <span className="text-[8px] font-bold text-[#d9532f]">
                $18.6M ARR
              </span>
            </div>
            <div className="my-auto space-y-1">
              <h4 className="text-xs font-extrabold text-[#261c14] tracking-tight leading-tight">
                The Next Generation of Sustainable Commerce
              </h4>
              <p className="text-[8px] text-[#5c4d40] line-clamp-1">
                Zero-waste regenerative goods crafted for conscious communities
              </p>
            </div>
            <div className="grid grid-cols-3 gap-1.5 bg-white border border-[#eedfcb] rounded-xl p-1 text-center shadow-xs">
              <div>
                <div className="text-[9px] font-extrabold text-[#d9532f]">185%</div>
                <div className="text-[6px] text-[#8c7b6d] uppercase">YoY Growth</div>
              </div>
              <div className="border-x border-[#eedfcb]">
                <div className="text-[9px] font-extrabold text-[#261c14]">72%</div>
                <div className="text-[6px] text-[#8c7b6d] uppercase">Repeat</div>
              </div>
              <div>
                <div className="text-[9px] font-extrabold text-[#f59e0b]">Zero</div>
                <div className="text-[6px] text-[#8c7b6d] uppercase">Plastic</div>
              </div>
            </div>
          </div>
        )

      // 13. Monochrome Monument: Stark High-Fashion Obsidian & Pure White
      case 'monochrome_monument':
      default:
        return (
          <div className="relative aspect-video w-full rounded-xl p-3.5 select-none flex flex-col justify-between overflow-hidden bg-[#050505] border border-[#222222] font-sans">
            <div className="flex items-center justify-between border-b border-[#222222] pb-1.5">
              <span className="text-[9px] font-mono tracking-[0.2em] text-white font-bold uppercase">
                MONUMENT // EXEC
              </span>
              <span className="text-[8px] font-mono text-zinc-400">
                $85B AUM
              </span>
            </div>
            <div className="my-auto space-y-1">
              <div className="text-[8px] tracking-[0.25em] text-zinc-400 uppercase font-mono">
                SOVEREIGN CAPITAL MANDATE
              </div>
              <h4 className="text-xs font-black text-white tracking-tight uppercase leading-tight">
                Strategic Capital &amp; Sovereign Execution
              </h4>
              <div className="w-10 h-[1.5px] bg-white my-1" />
            </div>
            <div className="flex items-center justify-between text-[7px] text-zinc-400 font-mono border-t border-[#222222] pt-1">
              <span>DECIL-ONE COMPOUND</span>
              <span className="text-white font-bold">34.2% NET IRR</span>
            </div>
          </div>
        )
    }
  }

  return (
    <article
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: mousePos.isHovered
          ? `perspective(1000px) rotateX(${mousePos.tiltX.toFixed(2)}deg) rotateY(${mousePos.tiltY.toFixed(2)}deg) translateY(-8px)`
          : 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)',
        transition: mousePos.isHovered
          ? 'transform 0.15s ease-out, box-shadow 0.3s ease, border-color 0.3s ease'
          : 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.5s ease, border-color 0.5s ease',
      }}
      className="group relative flex flex-col justify-between overflow-hidden liquid-glass-card rounded-2xl p-4 sm:p-5 select-none transition-all duration-300 hover:shadow-[0_24px_50px_-12px_rgba(0,0,0,0.85),0_0_40px_-10px_rgba(242,140,40,0.18)] hover:border-[#F28C28]/40"
    >
      {/* 1. Ambient Accent Bloom behind/around the card */}
      <div
        className="pointer-events-none absolute -inset-2 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-2xl z-0"
        style={{
          background: `radial-gradient(circle at 50% 25%, ${tmpl.accent || '#F28C28'}22 0%, transparent 70%)`,
        }}
      />

      {/* 2. Interactive Radial Cursor Spotlight across glass surface */}
      {mousePos.isHovered && (
        <div
          className="pointer-events-none absolute -inset-px rounded-2xl z-10 transition-opacity duration-200"
          style={{
            background: `radial-gradient(360px circle at ${mousePos.x}px ${mousePos.y}px, rgba(255, 255, 255, 0.08), transparent 70%)`,
          }}
        />
      )}

      {/* 3. Razor-thin Border Spotlight Highlight */}
      {mousePos.isHovered && (
        <div
          className="pointer-events-none absolute -inset-px rounded-2xl z-10"
          style={{
            background: `radial-gradient(220px circle at ${mousePos.x}px ${mousePos.y}px, ${tmpl.accent || '#F28C28'}70, transparent 70%)`,
            mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
            WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
            WebkitMaskComposite: 'xor',
            maskComposite: 'exclude',
            padding: '1px',
          }}
        />
      )}

      {/* 4. Top Rim Specular Line */}
      <div className="pointer-events-none absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 group-hover:via-[#F28C28]/90 to-transparent transition-all duration-500 z-20" />

      {/* Main Content Area */}
      <div className="relative z-10">
        {/* Top: Bespoke 16:9 Canvas */}
        <div
          onClick={() => onInspect?.(tmpl)}
          className="relative mb-4 cursor-pointer overflow-hidden rounded-xl shadow-md border border-white/[0.08] group-hover:border-white/[0.22] transition-all duration-500 group-hover:shadow-[0_12px_36px_rgba(0,0,0,0.65)]"
        >
          {/* Canvas container with micro scale */}
          <div className="transition-transform duration-500 ease-out group-hover:scale-[1.025]">
            {renderBespokeCanvas()}
          </div>

          {/* Diagonal Light Gleam Sweep on Hover */}
          <div className="pointer-events-none absolute inset-0 z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 overflow-hidden rounded-xl">
            <div className="absolute -inset-full top-0 block -skew-x-12 bg-gradient-to-r from-transparent via-white/[0.12] to-transparent group-hover:animate-card-gleam" />
          </div>

          {/* Quick 16:9 Studio Tag in Top Right */}
          <div className="pointer-events-none absolute top-2.5 right-2.5 z-20 opacity-0 group-hover:opacity-100 transition-all duration-300 scale-90 group-hover:scale-100 bg-[#101114]/85 backdrop-blur-md border border-white/20 text-[#F4E6D3] px-2 py-0.5 rounded-full text-[9px] font-mono tracking-wider uppercase flex items-center gap-1 shadow-lg">
            <span className="w-1.5 h-1.5 rounded-full bg-[#F28C28] animate-pulse" />
            <span>16:9 Studio</span>
          </div>

          {/* Subtle bottom gradient vignette for button contrast (keeps design fully visible!) */}
          <div className="pointer-events-none absolute inset-0 z-15 bg-gradient-to-t from-[#101114]/85 via-[#101114]/25 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl" />

          {/* Floating Glass Action Capsule */}
          <div className="absolute inset-x-0 bottom-2.5 z-20 flex items-center justify-center p-1 pointer-events-none">
            <div className="flex items-center gap-2 bg-[#17191E]/95 border border-white/[0.18] p-1.5 rounded-full shadow-[0_12px_32px_rgba(0,0,0,0.6)] backdrop-blur-xl translate-y-3 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 group-hover:pointer-events-auto transition-all duration-300 ease-out">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onInspect?.(tmpl)
                }}
                className="flex items-center gap-1.5 rounded-full bg-white/[0.08] hover:bg-white/[0.18] border border-white/[0.12] px-3.5 py-1.5 text-xs font-semibold text-[#F4E6D3] transition-all hover:scale-105 active:scale-95 cursor-pointer shadow-xs"
              >
                <Eye size={13} className="text-[#DFA36D]" />
                <span>Inspect</span>
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onUse?.(tmpl)
                }}
                className="flex items-center gap-1.5 rounded-full bg-[#F28C28] hover:bg-[#ff9a3c] px-3.5 py-1.5 text-xs font-bold text-[#101114] shadow-[0_0_16px_rgba(242,140,40,0.45)] hover:shadow-[0_0_24px_rgba(242,140,40,0.7)] transition-all hover:scale-105 active:scale-95 cursor-pointer"
              >
                <Zap size={13} />
                <span>Use System</span>
              </button>
            </div>
          </div>
        </div>

        {/* Metadata Details */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm sm:text-base font-bold text-[#F4E6D3] group-hover:text-white transition-colors tracking-tight">
              {tmpl.name}
            </h3>
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#DFA36D] px-2 py-0.5 rounded-md border border-white/[0.08] bg-white/[0.03] group-hover:border-[#F28C28]/35 group-hover:text-[#F28C28] transition-colors">
              {tmpl.category}
            </span>
          </div>

          <p className="line-clamp-2 text-xs text-[#888A90] group-hover:text-[#C5C0B8] transition-colors leading-relaxed">
            {tmpl.tagline}
          </p>

          {/* Feature Badges */}
          <div className="mt-3 flex flex-wrap gap-1.5 pt-1">
            {tmpl.features.slice(0, 3).map((f, i) => (
              <span
                key={i}
                className="rounded-md border border-white/[0.08] group-hover:border-white/[0.18] bg-white/[0.03] group-hover:bg-white/[0.06] px-2 py-0.5 text-[10px] font-medium text-[#C5C0B8] group-hover:text-[#F4E6D3] transition-all"
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Footer Swatches & Actions */}
      <div className="relative z-10 mt-4 flex items-center justify-between border-t border-white/[0.08] group-hover:border-white/[0.16] transition-colors pt-3">
        {/* Color Palette Swatches */}
        <div className="flex items-center gap-1.5">
          {[tmpl.bg, tmpl.cardBg, tmpl.accent].map((c, i) => (
            <div
              key={i}
              className="h-4 w-4 rounded-full border border-white/20 shadow-xs transition-all duration-200 group-hover:scale-110 hover:scale-135 hover:ring-2 hover:ring-white/50 cursor-pointer"
              style={{ backgroundColor: c }}
              title={`Palette hex: ${c}`}
            />
          ))}
          <span className="text-[10px] font-mono text-[#888A90] ml-1.5 opacity-60 group-hover:opacity-100 transition-opacity">
            Palette
          </span>
        </div>

        {/* Quick Footer Links */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => onInspect?.(tmpl)}
            className="text-xs font-medium text-[#C5C0B8] hover:text-[#F4E6D3] transition-colors cursor-pointer"
          >
            Inspect
          </button>
          <button
            onClick={() => onUse?.(tmpl)}
            className="group/btn flex items-center gap-1 text-xs font-semibold text-[#F28C28] hover:text-[#ff9a3c] transition-colors cursor-pointer"
          >
            <span>Use</span>
            <ArrowRight size={13} className="transition-transform duration-200 group-hover/btn:translate-x-1" />
          </button>
        </div>
      </div>
    </article>
  )
}

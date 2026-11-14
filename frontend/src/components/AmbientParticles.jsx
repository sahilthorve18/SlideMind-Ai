import { useEffect, useRef } from 'react'

/**
 * Obsidian Orange Palette Colors for Particles
 */
const COLORS = [
  { r: 242, g: 140, b: 40, weight: 0.45 }, // Amber #F28C28
  { r: 223, g: 163, b: 109, weight: 0.35 }, // Champagne #DFA36D
  { r: 244, g: 230, b: 211, weight: 0.20 }, // Warm Ivory #F4E6D3
]

function getRandomColor() {
  const rand = Math.random()
  let cumulative = 0
  for (const c of COLORS) {
    cumulative += c.weight
    if (rand <= cumulative) return c
  }
  return COLORS[0]
}

/**
 * AmbientParticles
 *
 * Cinematic HTML5 canvas particle system implementing the Obsidian Orange
 * ambient luxury technology aesthetic.
 *
 * Features:
 * - 3 depth planes (distant, midground, foreground) with varying speeds, opacities, and sizes
 * - Subtle constellation links between close particles
 * - Gentle organic floating motion with sinusoidal drift
 * - Interactive cursor repulsion (disabled on touch devices)
 * - Automatic pause on hidden tabs (document.hidden)
 * - Dynamic mobile scaling (<768px uses reduced particle density)
 * - Full respect for prefers-reduced-motion
 */
export default function AmbientParticles() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId = null
    let isMounted = true
    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)
    let dpr = window.devicePixelRatio || 1

    // Detect touch device
    const isTouch =
      typeof window !== 'undefined' &&
      ('ontouchstart' in window || navigator.maxTouchPoints > 0)

    // Detect prefers-reduced-motion
    let prefersReducedMotion = false
    try {
      prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    } catch {
      prefersReducedMotion = false
    }

    // Cursor tracking with smooth lerp
    const mouse = { x: -9999, y: -9999, radius: 130 }

    const handleMouseMove = (e) => {
      if (isTouch) return
      mouse.x = e.clientX
      mouse.y = e.clientY
    }

    const handleMouseLeave = () => {
      mouse.x = -9999
      mouse.y = -9999
    }

    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    document.addEventListener('mouseleave', handleMouseLeave, { passive: true })

    // Responsive particle count
    const getParticleCount = () => (window.innerWidth < 768 ? 26 : 65)

    // Particle factory
    const createParticle = (layerOverride) => {
      // 3 depth layers: 0 = distant, 1 = midground, 2 = foreground
      const layer = layerOverride ?? Math.floor(Math.random() * 3)
      const color = getRandomColor()

      let baseRadius, baseOpacity, baseSpeed
      if (layer === 0) {
        // Distant
        baseRadius = 0.8 + Math.random() * 0.7
        baseOpacity = 0.20 + Math.random() * 0.15
        baseSpeed = 0.12 + Math.random() * 0.18
      } else if (layer === 1) {
        // Midground
        baseRadius = 1.5 + Math.random() * 0.9
        baseOpacity = 0.35 + Math.random() * 0.20
        baseSpeed = 0.22 + Math.random() * 0.25
      } else {
        // Foreground
        baseRadius = 2.4 + Math.random() * 1.2
        baseOpacity = 0.55 + Math.random() * 0.25
        baseSpeed = 0.35 + Math.random() * 0.30
      }

      const angle = Math.random() * Math.PI * 2

      return {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: Math.cos(angle) * baseSpeed,
        vy: Math.sin(angle) * baseSpeed,
        radius: baseRadius,
        color,
        opacity: baseOpacity,
        layer,
        phase: Math.random() * Math.PI * 2,
        pulseSpeed: 0.008 + Math.random() * 0.015,
      }
    }

    let particles = []
    const initParticles = () => {
      const count = getParticleCount()
      particles = []
      for (let i = 0; i < count; i++) {
        particles.push(createParticle(i % 3))
      }
    }

    const resize = () => {
      dpr = window.devicePixelRatio || 1
      width = window.innerWidth
      height = window.innerHeight

      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.scale(dpr, dpr)

      initParticles()
    }

    resize()
    window.addEventListener('resize', resize)

    let lastTime = performance.now()

    // Draw single frame
    const render = (currentTime) => {
      const delta = Math.min((currentTime - lastTime) / 1000, 0.1)
      lastTime = currentTime

      ctx.clearRect(0, 0, width, height)

      // Connection threshold
      const maxConnectDist = width < 768 ? 85 : 115
      const numParticles = particles.length

      // 1. Draw connecting constellation lines
      for (let i = 0; i < numParticles; i++) {
        const p1 = particles[i]
        for (let j = i + 1; j < numParticles; j++) {
          const p2 = particles[j]
          const dx = p1.x - p2.x
          const dy = p1.y - p2.y
          const dist = Math.hypot(dx, dy)

          if (dist < maxConnectDist) {
            const lineAlpha = (1 - dist / maxConnectDist) * 0.13 * Math.min(p1.opacity, p2.opacity)
            ctx.beginPath()
            ctx.moveTo(p1.x, p1.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.strokeStyle = `rgba(242, 140, 40, ${lineAlpha})`
            ctx.lineWidth = 0.75
            ctx.stroke()
          }
        }
      }

      // 2. Update and draw particles
      for (let i = 0; i < numParticles; i++) {
        const p = particles[i]

        if (!prefersReducedMotion) {
          // Organic sinusoidal drift
          p.x += p.vx + Math.cos(currentTime * 0.001 + p.phase) * 0.15
          p.y += p.vy + Math.sin(currentTime * 0.0012 + p.phase) * 0.20

          // Subtle interactive cursor repulsion
          if (!isTouch && mouse.x > 0 && mouse.y > 0) {
            const mdx = p.x - mouse.x
            const mdy = p.y - mouse.y
            const mdist = Math.hypot(mdx, mdy)

            if (mdist < mouse.radius && mdist > 0) {
              const force = (1 - mdist / mouse.radius) * 1.2
              p.x += (mdx / mdist) * force
              p.y += (mdy / mdist) * force
            }
          }

          // Screen edge wrapping with smooth buffer
          const buffer = 15
          if (p.x < -buffer) p.x = width + buffer
          if (p.x > width + buffer) p.x = -buffer
          if (p.y < -buffer) p.y = height + buffer
          if (p.y > height + buffer) p.y = -buffer
        }

        // Subtle pulsing opacity
        const pulse = Math.sin(currentTime * p.pulseSpeed + p.phase) * 0.1
        const currentOpacity = Math.max(0.08, Math.min(0.9, p.opacity + pulse))

        // Particle rendering
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, ${currentOpacity})`
        ctx.fill()

        // Subtle warm glow for foreground particles
        if (p.layer === 2) {
          ctx.beginPath()
          ctx.arc(p.x, p.y, p.radius * 2.2, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, ${currentOpacity * 0.22})`
          ctx.fill()
        }
      }

      if (!prefersReducedMotion && isMounted) {
        animationFrameId = requestAnimationFrame(render)
      }
    }

    // Start RAF loop
    animationFrameId = requestAnimationFrame(render)

    // Handle tab visibility (pause loop when backgrounded)
    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId)
          animationFrameId = null
        }
      } else {
        if (!animationFrameId && !prefersReducedMotion && isMounted) {
          lastTime = performance.now()
          animationFrameId = requestAnimationFrame(render)
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      isMounted = false
      if (animationFrameId) cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseleave', handleMouseLeave)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
    />
  )
}

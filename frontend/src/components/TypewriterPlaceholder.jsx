import { useEffect, useRef, useState } from 'react'

/**
 * PROMPT SPECIFICATIONS
 * Each prompt has a warm ivory prefix and an editorial champagne highlight segment.
 */
const PROMPT_SEGMENTS = [
  {
    prefix: 'Create a premium presentation about ',
    highlight: 'Artificial Intelligence.',
  },
  {
    prefix: 'Design a cinematic investor pitch deck ',
    highlight: 'for a startup.',
  },
  {
    prefix: 'Explain quantum computing ',
    highlight: 'with beautiful visual diagrams.',
  },
  {
    prefix: 'Create a business strategy presentation ',
    highlight: 'for 2027.',
  },
  {
    prefix: 'Build a presentation about ',
    highlight: 'the future of technology.',
  },
]

/**
 * TypewriterPlaceholder
 *
 * Implements an Apple Liquid Glass aesthetic animated typewriter placeholder
 * that cycles through curated prompts with warm ivory typography, champagne accents,
 * and a small blinking amber cursor.
 *
 * Requirements:
 * - Natural variable typing speed (45–65ms)
 * - Pause at completion (1.8–2.5s)
 * - Variable deleting speed (25–35ms)
 * - Pauses immediately when user focuses or clicks composer
 * - Hides completely when user enters any text
 * - Resumes gracefully after blur + idle delay
 * - Respects prefers-reduced-motion
 * - Pointer-events-none: never intercepts clicks or typing
 */
export default function TypewriterPlaceholder({
  isFocused = false,
  hasText = false,
}) {
  const [displayText, setDisplayText] = useState({ prefix: '', highlight: '' })
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

  // Internal refs to preserve state machine across renders without re-triggering loops
  const timeoutRef = useRef(null)
  const charIdxRef = useRef(0)
  const isTypingRef = useRef(true)
  const promptIdxRef = useRef(0)
  const isPausedRef = useRef(false)

  // Detect prefers-reduced-motion
  useEffect(() => {
    try {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
      setPrefersReducedMotion(mediaQuery.matches)

      const handleChange = (e) => setPrefersReducedMotion(e.matches)
      mediaQuery.addEventListener?.('change', handleChange)
      return () => mediaQuery.removeEventListener?.('change', handleChange)
    } catch {
      setPrefersReducedMotion(false)
    }
  }, [])

  // Keep paused state in sync
  useEffect(() => {
    isPausedRef.current = isFocused || hasText
  }, [isFocused, hasText])

  useEffect(() => {
    // If reduced motion is requested, show first prompt statically
    if (prefersReducedMotion) {
      const p = PROMPT_SEGMENTS[0]
      setDisplayText({ prefix: p.prefix, highlight: p.highlight })
      return
    }

    // If user has typed text or is focused, suspend animation
    if (hasText || isFocused) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      return
    }

    let isMounted = true

    const clearActiveTimeout = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
    }

    const updateDisplay = (idx, charCount) => {
      const currentSegment = PROMPT_SEGMENTS[idx % PROMPT_SEGMENTS.length]
      const prefixLen = currentSegment.prefix.length

      if (charCount <= prefixLen) {
        setDisplayText({
          prefix: currentSegment.prefix.slice(0, charCount),
          highlight: '',
        })
      } else {
        const highlightCount = charCount - prefixLen
        setDisplayText({
          prefix: currentSegment.prefix,
          highlight: currentSegment.highlight.slice(0, highlightCount),
        })
      }
    }

    const step = () => {
      if (!isMounted || isPausedRef.current) return

      const currentSegment = PROMPT_SEGMENTS[promptIdxRef.current % PROMPT_SEGMENTS.length]
      const fullLength = currentSegment.prefix.length + currentSegment.highlight.length

      if (isTypingRef.current) {
        // Typing forward
        if (charIdxRef.current < fullLength) {
          charIdxRef.current += 1
          updateDisplay(promptIdxRef.current, charIdxRef.current)

          // 45–65ms typing delay per char with humanized jitter
          const delay = 45 + Math.floor(Math.random() * 20)
          timeoutRef.current = setTimeout(step, delay)
        } else {
          // Completed typing full prompt -> Pause for 1.8–2.5s
          isTypingRef.current = false
          const pauseDuration = 1800 + Math.floor(Math.random() * 700)
          timeoutRef.current = setTimeout(step, pauseDuration)
        }
      } else {
        // Deleting backward
        if (charIdxRef.current > 0) {
          charIdxRef.current -= 1
          updateDisplay(promptIdxRef.current, charIdxRef.current)

          // 25–35ms deleting delay per char
          const deleteDelay = 25 + Math.floor(Math.random() * 10)
          timeoutRef.current = setTimeout(step, deleteDelay)
        } else {
          // Finished deleting -> Advance to next prompt after a 350ms pause
          promptIdxRef.current = (promptIdxRef.current + 1) % PROMPT_SEGMENTS.length
          isTypingRef.current = true
          timeoutRef.current = setTimeout(step, 350)
        }
      }
    }

    // Initial wait: approximately 800ms after composer becomes ready (or resumes after blur)
    clearActiveTimeout()
    const initialDelay = charIdxRef.current === 0 ? 800 : 900
    timeoutRef.current = setTimeout(step, initialDelay)

    return () => {
      isMounted = false
      clearActiveTimeout()
    }
  }, [hasText, isFocused, prefersReducedMotion])

  // If user has entered text, the animated placeholder remains completely hidden
  if (hasText) {
    return null
  }

  return (
    <div
      aria-hidden="true"
      className={`absolute inset-0 pointer-events-none select-none overflow-hidden transition-opacity duration-200 ${
        isFocused ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <div className="text-sm sm:text-base font-normal tracking-tight leading-relaxed">
        {/* Warm ivory main text */}
        <span className="text-[#F4E6D3]/75">{displayText.prefix}</span>
        {/* Subtle champagne highlight accent */}
        {displayText.highlight && (
          <span className="text-[#DFA36D] font-medium">{displayText.highlight}</span>
        )}
        {/* Small blinking amber cursor */}
        <span className="typewriter-cursor" />
      </div>
    </div>
  )
}

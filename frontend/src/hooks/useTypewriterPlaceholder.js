import { useEffect, useRef, useState } from 'react'

/**
 * ROTATING EXAMPLE PROMPTS
 * Curated editorial examples for SlideMind AI Studio.
 */
const EXAMPLE_PROMPTS = [
  'Create a premium presentation about Artificial Intelligence.',
  'Design a cinematic investor pitch deck for a startup.',
  'Explain quantum computing with beautiful visual diagrams.',
  'Create a business strategy presentation for 2027.',
  'Build a presentation about the future of technology.',
]

/**
 * useTypewriterPlaceholder
 *
 * Custom hook that animates the native placeholder of a textarea/input element.
 *
 * Key guarantees:
 * 1. 100% exact alignment with user text (padding, line-height, font-family, font-size).
 * 2. Persistent stopping: the first time the user focuses, clicks, or types in the composer,
 *    the typewriter animation permanently halts for that page session.
 * 3. Never restarts on blur, mouse leave, or clearing text.
 * 4. Blinking cursor character immediately follows the typed text.
 * 5. Respects prefers-reduced-motion and document visibility.
 * 6. Completely cleans up all timeouts and intervals on unmount.
 */
export function useTypewriterPlaceholder({
  defaultPlaceholder = 'What would you like to create today?',
  prompts = EXAMPLE_PROMPTS,
} = {}) {
  // Whether user has interacted (focus, click, typing) in this page session
  const [hasInteracted, setHasInteracted] = useState(false)
  const hasInteractedRef = useRef(false)

  // Current animated text
  const [currentText, setCurrentText] = useState('')
  const [isCursorVisible, setIsCursorVisible] = useState(true)

  // State machine tracking refs
  const timeoutRef = useRef(null)
  const blinkIntervalRef = useRef(null)
  const promptIdxRef = useRef(0)
  const charIdxRef = useRef(0)
  const isTypingRef = useRef(true)

  // Trigger permanent stop on first user interaction
  const handleInteraction = () => {
    if (!hasInteractedRef.current) {
      hasInteractedRef.current = true
      setHasInteracted(true)

      // Immediately cancel all pending animation loops
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      if (blinkIntervalRef.current) {
        clearInterval(blinkIntervalRef.current)
        blinkIntervalRef.current = null
      }
    }
  }

  useEffect(() => {
    // If already interacted, never run the animation loop
    if (hasInteractedRef.current) return

    // Check prefers-reduced-motion
    let prefersReducedMotion = false
    try {
      prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    } catch {
      prefersReducedMotion = false
    }

    if (prefersReducedMotion) {
      setCurrentText(prompts[0] || defaultPlaceholder)
      return
    }

    let isMounted = true

    // Blink cursor during pauses and typing
    blinkIntervalRef.current = setInterval(() => {
      if (!hasInteractedRef.current && isMounted) {
        setIsCursorVisible((v) => !v)
      }
    }, 500)

    const clearTimers = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
    }

    const step = () => {
      if (!isMounted || hasInteractedRef.current) return

      const currentPrompt = prompts[promptIdxRef.current % prompts.length]
      const fullLength = currentPrompt.length

      if (isTypingRef.current) {
        // Typing forward
        if (charIdxRef.current < fullLength) {
          charIdxRef.current += 1
          setCurrentText(currentPrompt.slice(0, charIdxRef.current))

          // 45–65ms typing delay per char with slight human jitter
          const delay = 45 + Math.floor(Math.random() * 20)
          timeoutRef.current = setTimeout(step, delay)
        } else {
          // Finished typing full prompt -> Pause for 1.8–2.5s
          isTypingRef.current = false
          const pauseDuration = 1800 + Math.floor(Math.random() * 700)
          timeoutRef.current = setTimeout(step, pauseDuration)
        }
      } else {
        // Deleting backward
        if (charIdxRef.current > 0) {
          charIdxRef.current -= 1
          setCurrentText(currentPrompt.slice(0, charIdxRef.current))

          // 25–35ms deleting delay per char
          const deleteDelay = 25 + Math.floor(Math.random() * 10)
          timeoutRef.current = setTimeout(step, deleteDelay)
        } else {
          // Finished deleting -> Advance to next prompt after a 350ms pause
          promptIdxRef.current = (promptIdxRef.current + 1) % prompts.length
          isTypingRef.current = true
          timeoutRef.current = setTimeout(step, 350)
        }
      }
    }

    // Initial wait: ~800ms after composer becomes ready
    timeoutRef.current = setTimeout(step, 800)

    return () => {
      isMounted = false
      clearTimers()
      if (blinkIntervalRef.current) {
        clearInterval(blinkIntervalRef.current)
        blinkIntervalRef.current = null
      }
    }
  }, [prompts, defaultPlaceholder])

  // If the user has interacted, use the static default placeholder without cursor
  if (hasInteracted) {
    return {
      placeholder: defaultPlaceholder,
      hasInteracted: true,
      handleInteraction,
    }
  }

  // Active typewriter mode with natural blinking cursor
  const cursorChar = isCursorVisible ? ' ❘' : '  '
  const animatedPlaceholder = currentText ? `${currentText}${cursorChar}` : cursorChar

  return {
    placeholder: animatedPlaceholder,
    hasInteracted: false,
    handleInteraction,
  }
}

export default useTypewriterPlaceholder

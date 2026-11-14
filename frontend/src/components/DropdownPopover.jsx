import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

/**
 * DropdownPopover.jsx
 * A robust, portal-based floating popover attached directly to document.body.
 * Escapes all CSS stacking contexts, overflow clipping, and z-index traps.
 * Automatically flips upward when there is insufficient space below the trigger.
 */
export default function DropdownPopover({
  triggerRef,
  isOpen,
  onClose,
  children,
  widthClass = 'w-76 sm:w-92',
}) {
  const [style, setStyle] = useState({
    top: undefined,
    bottom: undefined,
    left: 16,
    opensUp: false,
    maxHeight: 288,
  })
  const popoverRef = useRef(null)

  const updatePosition = () => {
    if (!triggerRef?.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    const viewportHeight = window.innerHeight
    const viewportWidth = window.innerWidth

    const spaceBelow = viewportHeight - rect.bottom
    const spaceAbove = rect.top
    const estimatedHeight = 300 // typical height of 9-style list
    const opensUp = spaceBelow < estimatedHeight && spaceAbove > spaceBelow

    // Compute optimal horizontal alignment
    const isMobile = viewportWidth < 640
    const measuredWidth = popoverRef.current?.offsetWidth || (isMobile ? Math.min(320, viewportWidth - 32) : 368)
    let left = rect.left
    if (left + measuredWidth > viewportWidth - 16) {
      left = Math.max(16, viewportWidth - measuredWidth - 16)
    }
    left = Math.max(16, left)

    if (opensUp) {
      const bottom = viewportHeight - rect.top + 8
      const availableHeight = Math.max(160, Math.min(320, spaceAbove - 24))
      setStyle({
        top: undefined,
        bottom,
        left,
        opensUp: true,
        maxHeight: availableHeight,
      })
    } else {
      const top = rect.bottom + 8
      const availableHeight = Math.max(160, Math.min(320, spaceBelow - 24))
      setStyle({
        top,
        bottom: undefined,
        left,
        opensUp: false,
        maxHeight: availableHeight,
      })
    }
  }

  useLayoutEffect(() => {
    if (isOpen) {
      updatePosition()
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return

    const handleResize = () => updatePosition()
    const handleScroll = () => updatePosition()
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.()
    }

    window.addEventListener('resize', handleResize)
    window.addEventListener('scroll', handleScroll, true)
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('scroll', handleScroll, true)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return createPortal(
    <div className="dropdown-portal-root fixed inset-0 z-[9999] pointer-events-auto">
      {/* Invisible backdrop to dismiss on click outside */}
      <div
        className="fixed inset-0 bg-transparent z-[9998]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Floating Popover Container */}
      <div
        ref={popoverRef}
        style={{
          position: 'fixed',
          ...(style.bottom !== undefined ? { bottom: `${style.bottom}px` } : { top: `${style.top}px` }),
          left: `${style.left}px`,
        }}
        className={`${widthClass} max-w-[calc(100vw-32px)] liquid-glass-popover p-2.5 z-[9999] animate-in fade-in ${
          style.opensUp ? 'slide-in-from-bottom-2' : 'slide-in-from-top-2'
        } duration-150`}
      >
        {typeof children === 'function' ? children({ maxHeight: style.maxHeight }) : children}
      </div>
    </div>,
    document.body
  )
}

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Plus,
  MessageSquare,
  Sparkles,
  FileText,
  Settings,
  Palette,
  Layers,
  ArrowRight,
  X,
  Command,
  Presentation as PresentationIcon,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import { DESIGN_SYSTEMS } from '../services/designSystems'
import { api } from '../services/api'

export default function CommandPalette() {
  const {
    commandPaletteOpen,
    setCommandPaletteOpen,
    updatePreferences,
    toast,
    user,
  } = useApp()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [recentPresentations, setRecentPresentations] = useState([])
  const [recentChats, setRecentChats] = useState([])
  const inputRef = useRef(null)
  const listRef = useRef(null)

  // Global Keyboard listener for ⌘K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault()
        setCommandPaletteOpen((prev) => !prev)
      } else if (e.key === 'Escape' && commandPaletteOpen) {
        e.preventDefault()
        setCommandPaletteOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [commandPaletteOpen, setCommandPaletteOpen])

  // Focus input when opened and fetch recents
  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery('')
      setSelectedIndex(0)
      requestAnimationFrame(() => inputRef.current?.focus())

      // Fetch user recent presentations & chats if authenticated
      if (user) {
        api.presentations()
          .then((data) => setRecentPresentations(Array.isArray(data) ? data.slice(0, 5) : []))
          .catch(() => setRecentPresentations([]))

        api.history()
          .then((data) => setRecentChats(Array.isArray(data) ? data.slice(0, 5) : []))
          .catch(() => setRecentChats([]))
      } else {
        setRecentPresentations([])
        setRecentChats([])
      }
    }
  }, [commandPaletteOpen])

  if (!commandPaletteOpen) return null

  // Base Actions
  const staticActions = [
    {
      id: 'new-deck',
      category: 'Quick Actions',
      title: 'Create New Presentation',
      subtitle: 'Start with guided topic & design system generator',
      icon: Plus,
      badge: 'Action',
      onSelect: () => {
        setCommandPaletteOpen(false)
        navigate('/presentations/new')
      },
    },
    {
      id: 'new-chat',
      category: 'Quick Actions',
      title: 'Start Fresh Conversation',
      subtitle: 'Open an empty Studio workspace session',
      icon: MessageSquare,
      badge: 'Chat',
      onSelect: () => {
        setCommandPaletteOpen(false)
        sessionStorage.removeItem('sm_active_chat')
        navigate('/chat')
      },
    },
    {
      id: 'explore-templates',
      category: 'Navigation',
      title: 'Explore Creative Directions',
      subtitle: 'Browse 9 curated architectural aesthetic systems',
      icon: Layers,
      badge: 'View',
      onSelect: () => {
        setCommandPaletteOpen(false)
        navigate('/templates')
      },
    },
    {
      id: 'my-presentations',
      category: 'Navigation',
      title: 'My Presentations',
      subtitle: 'Manage saved decks, analytics, and exports',
      icon: PresentationIcon,
      badge: 'View',
      onSelect: () => {
        setCommandPaletteOpen(false)
        navigate('/presentations')
      },
    },
  ]

  // Design Systems Actions
  const designSystemActions = DESIGN_SYSTEMS.map((ds) => ({
    id: `ds-${ds.id}`,
    category: 'Design Systems',
    title: ds.name,
    subtitle: ds.tagline,
    accent: ds.accent,
    icon: Palette,
    badge: ds.category.split('&')[0].trim(),
    onSelect: () => {
      setCommandPaletteOpen(false)
      updatePreferences({ defaultDesignSystem: ds.id })
      toast(`Design System set to ${ds.name}`, 'success')
      navigate('/chat')
    },
  }))

  // Dynamic Recent Presentations
  const presentationActions = recentPresentations.map((p) => ({
    id: `p-${p.id}`,
    category: 'Recent Presentations',
    title: p.title || 'Untitled Presentation',
    subtitle: `${p.slide_count || 10} slides · ${p.google_url ? 'Google Slides' : 'Native Deck'}`,
    icon: Sparkles,
    badge: 'Deck',
    onSelect: () => {
      setCommandPaletteOpen(false)
      navigate(`/presentations/${p.id}`)
    },
  }))

  // Dynamic Recent Chats
  const chatActions = recentChats.map((c) => ({
    id: `chat-${c.id}`,
    category: 'Past Chats',
    title: c.title || 'Untitled Conversation',
    subtitle: `Updated ${new Date(c.updated_at).toLocaleDateString()}`,
    icon: MessageSquare,
    badge: 'History',
    onSelect: () => {
      setCommandPaletteOpen(false)
      navigate(`/chat/${c.id}`)
    },
  }))

  const allItems = [
    ...staticActions,
    ...presentationActions,
    ...designSystemActions,
    ...chatActions,
  ]

  const cleanQ = query.trim().toLowerCase()
  const filtered = cleanQ
    ? allItems.filter(
        (item) =>
          item.title.toLowerCase().includes(cleanQ) ||
          item.subtitle.toLowerCase().includes(cleanQ) ||
          item.category.toLowerCase().includes(cleanQ)
      )
    : allItems

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filtered.length))
      scrollIntoView((selectedIndex + 1) % Math.max(1, filtered.length))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length))
      scrollIntoView((selectedIndex - 1 + filtered.length) % Math.max(1, filtered.length))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].onSelect()
      }
    }
  }

  const scrollIntoView = (index) => {
    const list = listRef.current
    if (!list) return
    const el = list.querySelector(`[data-index="${index}"]`)
    if (el) {
      el.scrollIntoView({ block: 'nearest' })
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 sm:pt-28 px-4 bg-black/75 backdrop-blur-md"
      onClick={() => setCommandPaletteOpen(false)}
    >
      <div
        className="w-full max-w-2xl overflow-hidden rounded-2xl liquid-glass-modal border border-white/[0.14] shadow-[0_24px_60px_rgba(0,0,0,0.85)] animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="relative flex items-center border-b border-white/[0.08] px-4 py-3.5 bg-[#17191E]/60">
          <Search size={18} className="text-[#F28C28] shrink-0 mr-3" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command, design style, or search presentations..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            onKeyDown={handleKeyDown}
            className="w-full bg-transparent border-0 p-0 text-sm sm:text-base text-[#F4E6D3] placeholder:text-[#888A90] focus:ring-0 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(false)}
            className="p-1 rounded-lg text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/[0.08] transition-colors cursor-pointer shrink-0 ml-2"
          >
            <X size={16} />
          </button>
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          className="max-h-[60vh] overflow-y-auto p-2 space-y-1 scrollbar-thin"
        >
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#888A90] space-y-2">
              <Command size={24} className="mx-auto text-[#888A90]/60 mb-2" />
              <p className="text-sm font-medium text-[#F4E6D3]">No commands matching &ldquo;{query}&rdquo;</p>
              <p>Try searching for &ldquo;new&rdquo;, &ldquo;templates&rdquo;, &ldquo;linear&rdquo;, or &ldquo;pitch&rdquo;.</p>
            </div>
          ) : (
            filtered.map((item, idx) => {
              const isSelected = idx === selectedIndex
              const IconComp = item.icon
              return (
                <button
                  key={item.id}
                  data-index={idx}
                  type="button"
                  onClick={item.onSelect}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-left transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#F28C28]/16 border border-[#F28C28]/35 shadow-sm text-[#F4E6D3]'
                      : 'hover:bg-white/[0.05] text-[#C5C0B8] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${
                        isSelected
                          ? 'bg-[#F28C28]/25 border-[#F28C28]/40 text-[#F28C28]'
                          : 'bg-white/[0.05] border-white/[0.08] text-[#888A90]'
                      }`}
                    >
                      {item.accent ? (
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: item.accent }}
                        />
                      ) : (
                        <IconComp size={15} />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs sm:text-sm font-semibold truncate text-[#F4E6D3]">
                        {item.title}
                      </div>
                      <div className="text-[11px] text-[#888A90] truncate leading-tight mt-0.5">
                        {item.subtitle}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md border border-white/10 bg-white/[0.02] text-[#888A90] uppercase tracking-wider">
                      {item.badge}
                    </span>
                    {isSelected && (
                      <ArrowRight size={13} className="text-[#F28C28]" />
                    )}
                  </div>
                </button>
              )
            })
          )}
        </div>

        {/* Bottom Keyboard Legend */}
        <div className="flex items-center justify-between border-t border-white/[0.06] bg-[#101114]/80 px-4 py-2 text-[10px] font-mono text-[#888A90]">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-white/[0.08] border border-white/10 text-[#C5C0B8]">↑</kbd>
              {' '}
              <kbd className="px-1.5 py-0.5 rounded bg-white/[0.08] border border-white/10 text-[#C5C0B8]">↓</kbd>
              {' '}Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-white/[0.08] border border-white/10 text-[#C5C0B8]">↵</kbd>
              {' '}Select
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-white/[0.08] border border-white/10 text-[#C5C0B8]">esc</kbd>
              {' '}Close
            </span>
          </div>
          <span className="text-[#DFA36D]">SlideMind Spotlight</span>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'

/**
 * ChatSidebar.jsx
 * Liquid glass sidebar with curved edges for starting a New Chat
 * and accessing/managing previous chat conversations.
 */
export default function ChatSidebar({
  conversationId,
  onSelectConversation,
  onNewChat,
  isOpen,
  onToggle,
}) {
  const { user, toast } = useApp()
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  const loadHistory = async (silent = false) => {
    if (!user) return
    if (!silent) setLoading(true)
    try {
      const history = await api.history()
      setConversations(history || [])
    } catch (e) {
      console.error('Failed to load chat history:', e)
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    loadHistory(conversations.length > 0)
  }, [user, conversationId])

  const handleSelectConversation = (id) => {
    onSelectConversation(id)
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      onToggle?.()
    }
  }

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (deletingId) return
    setDeletingId(id)
    try {
      await api.deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      toast('Conversation deleted', 'info')
      if (conversationId === id) {
        onNewChat?.()
      }
    } catch (err) {
      toast(err.message || 'Failed to delete conversation', 'error')
    } finally {
      setDeletingId(null)
    }
  }

  const filtered = conversations.filter((c) =>
    (c.title || 'Untitled conversation').toLowerCase().includes(search.toLowerCase())
  )

  const formatTimestamp = (isoString) => {
    if (!isoString) return ''
    try {
      const date = new Date(isoString)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 2) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays === 1) return 'Yesterday'
      if (diffDays < 7) return `${diffDays}d ago`
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    } catch {
      return ''
    }
  }

  return (
    <>
      {/* Liquid Glass Toggle Button when Sidebar is closed */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ opacity: 0, scale: 0.85, x: -10 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.85, x: -10 }}
            transition={{ duration: 0.2 }}
            onClick={onToggle}
            title="Open Conversations (Old Chats)"
            className="fixed left-5 top-24 z-40 flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.12] hover:border-[#F28C28]/40 shadow-[0_8px_30px_rgb(0,0,0,0.4)] backdrop-blur-2xl text-[#F4E6D3] transition-all cursor-pointer group"
          >
            <span className="material-symbols-outlined text-[#F28C28] text-xl transition-transform duration-200 group-hover:scale-110">
              history
            </span>
            <span className="text-xs font-label-md text-[#C5C0B8] group-hover:text-[#F4E6D3] tracking-wide">
              Chats
            </span>
            {conversations.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-[#F28C28]/20 text-[#F28C28] border border-[#F28C28]/35 font-mono">
                {conversations.length}
              </span>
            )}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Floating Liquid Glass Sidebar */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Mobile backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onToggle}
              className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            />

            <motion.aside
              initial={{ x: -320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -320, opacity: 0 }}
              transition={{ type: 'spring', damping: 26, stiffness: 240 }}
              className="fixed left-4 top-24 bottom-6 w-72 z-50 flex flex-col rounded-3xl bg-[#101114]/90 border border-white/[0.12] shadow-[0_20px_60px_rgba(0,0,0,0.8)] backdrop-blur-2xl overflow-hidden before:absolute before:inset-0 before:rounded-3xl before:bg-gradient-to-b before:from-white/[0.07] before:to-transparent before:pointer-events-none"
            >
              {/* Header Bar */}
              <div className="relative z-10 flex items-center justify-between px-5 pt-4 pb-3 border-b border-white/[0.06]">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-[#F28C28]/30 to-[#DFA36D]/20 border border-[#F28C28]/35 flex items-center justify-center">
                    <span className="material-symbols-outlined text-[#F28C28] text-sm">
                      chat_bubble
                    </span>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-[#F4E6D3] tracking-wide uppercase font-mono">
                      Conversations
                    </h3>
                  </div>
                </div>

                <button
                  onClick={onToggle}
                  title="Collapse sidebar"
                  className="w-7 h-7 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 flex items-center justify-center text-[#888A90] hover:text-[#F4E6D3] transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-base">
                    dock_to_left
                  </span>
                </button>
              </div>

              {/* Action Button: NEW CHAT */}
              <div className="relative z-10 p-4 pb-3">
                <button
                  onClick={onNewChat}
                  className="w-full flex items-center justify-center gap-2.5 py-3 px-4 rounded-2xl liquid-glass-btn-primary text-[#101114] font-semibold text-xs tracking-wide cursor-pointer group"
                >
                  <span className="material-symbols-outlined text-[#101114] text-lg transition-transform duration-200 group-hover:rotate-90">
                    add
                  </span>
                  <span>New Presentation Chat</span>
                </button>
              </div>

              {/* Search Filter for Old Chats */}
              {conversations.length > 5 && (
                <div className="relative z-10 px-4 pb-2">
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-2.5 text-[#888A90] text-sm pointer-events-none">
                      search
                    </span>
                    <input
                      type="text"
                      placeholder="Filter chats…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="w-full rounded-xl bg-[#1E2026] border border-white/[0.10] pl-8 pr-3 py-1.5 text-xs text-[#F4E6D3] placeholder-[#888A90] focus:outline-none focus:border-[#F28C28] transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Old Chats List */}
              <div className="relative z-10 flex-1 px-3 py-2 overflow-y-auto space-y-1.5 custom-scrollbar">
                <div className="px-2 pt-1 pb-1 flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-[#888A90]">
                  <span>Recent Chats</span>
                  <span>{filtered.length}</span>
                </div>

                {loading && conversations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-[#888A90] text-xs">
                    <span className="material-symbols-outlined animate-spin text-[#F28C28] mb-2">
                      autorenew
                    </span>
                    <span>Loading history…</span>
                  </div>
                ) : filtered.length === 0 ? (
                  <div className="text-center py-10 px-3 text-[#888A90] text-xs">
                    {search ? 'No matching chats found' : 'No previous conversations yet.'}
                  </div>
                ) : (
                  filtered.map((c) => {
                    const isActive = c.id === conversationId
                    const isDeleting = deletingId === c.id

                    return (
                      <div
                        key={c.id}
                        onClick={() => handleSelectConversation(c.id)}
                        className={`group relative flex items-center justify-between p-2.5 rounded-2xl border transition-all duration-200 cursor-pointer ${
                          isActive
                            ? 'bg-white/[0.08] border-[#F28C28]/50 shadow-[0_4px_16px_rgba(242,140,40,0.20)] text-[#F4E6D3]'
                            : 'bg-white/[0.02] hover:bg-white/[0.06] border-white/[0.05] hover:border-white/15 text-[#C5C0B8] hover:text-[#F4E6D3]'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0 flex-1">
                          <span
                            className={`material-symbols-outlined text-base flex-shrink-0 ${
                              isActive ? 'text-[#F28C28]' : 'text-[#888A90] group-hover:text-[#C5C0B8]'
                            }`}
                          >
                            {c.active_presentation_id ? 'slideshow' : 'forum'}
                          </span>

                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-medium truncate leading-tight">
                              {c.title || 'Untitled conversation'}
                            </p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-[10px] text-[#888A90] font-mono">
                                {formatTimestamp(c.updated_at)}
                              </span>
                              {c.active_presentation_id && (
                                <span className="text-[9px] px-1 py-0.2 rounded bg-[#F28C28]/20 text-[#F28C28] border border-[#F28C28]/30 font-mono uppercase">
                                  Deck
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Delete button on hover */}
                        <button
                          onClick={(e) => handleDelete(e, c.id)}
                          disabled={isDeleting}
                          title="Delete chat"
                          className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-red-500/20 text-[#888A90] hover:text-red-400 transition-all cursor-pointer ml-1 flex-shrink-0"
                        >
                          <span className="material-symbols-outlined text-sm">
                            {isDeleting ? 'autorenew' : 'delete'}
                          </span>
                        </button>
                      </div>
                    )
                  })
                )}
              </div>

              {/* Liquid Glass Footer Island */}
              <div className="relative z-10 p-3 pt-2 border-t border-white/[0.06] bg-black/30 flex items-center justify-between text-[11px] text-[#888A90]">
                <span className="font-mono">SlideMind Studio</span>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/10 text-[#C5C0B8]">
                  AI v4.2
                </span>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}

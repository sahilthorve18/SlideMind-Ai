import ModernTemplateCard from '../components/ModernTemplateCard'
import { DESIGN_SYSTEMS } from '../services/designSystems'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import ChatInput from '../components/ChatInput'
import ChatDeckPreview from '../components/ChatDeckPreview'
import JobProgress from '../components/JobProgress'
import ChatSidebar from '../components/ChatSidebar'
import PresenterModal from '../components/PresenterModal'
import ErrorBoundary from '../components/ErrorBoundary'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'

export default function Chat({
  conversationId,
  onConversationChange,
  onMenu,
  refreshHistory,
  presentation,
  onClearPresentation,
  onOpenPresentations,
  onOpenTemplates,
}) {
  const {
    toast,
    activeJobId,
    setActiveJobId,
    activePresentationId,
    setActivePresentationId,
    notifyPresentationsUpdated,
    setCommandPaletteOpen,
  } = useApp()
  const navigate = useNavigate()
  const [messages, setMessages] = useState(() => {
    try {
      const initPrompt = typeof window !== 'undefined' ? sessionStorage.getItem('initialPrompt') : null
      if (initPrompt) {
        const cleanText = initPrompt.replace(/\[Style:[^\]]+\]/gi, '').replace(/\[Deep Research\]/gi, '').trim() || initPrompt
        if (cleanText) {
          return [{ id: 'optimistic-initial-prompt', role: 'user', content: cleanText }]
        }
      }
    } catch {}
    return []
  })
  const [busy, setBusy] = useState(() => {
    try {
      return typeof window !== 'undefined' && Boolean(sessionStorage.getItem('initialPrompt'))
    } catch {
      return false
    }
  })
  const [loadingConversation, setLoadingConversation] = useState(false)
  const [conversationError, setConversationError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [citation, setCitation] = useState(null)
  const [presenterDeck, setPresenterDeck] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      if (typeof window !== 'undefined' && window.innerWidth < 1024) {
        return false
      }
      const saved = localStorage.getItem('sm_chat_sidebar_open')
      return saved === null ? true : saved === 'true'
    } catch {
      return false
    }
  })
  const endRef = useRef(null)
  const prevMsgCountRef = useRef(0)
  const prevConvIdRef = useRef(conversationId)
  const skipLoadFor = useRef(null)
  const isSendingRef = useRef(false)
  const abortControllerRef = useRef(null)

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (activeJobId) {
      setActiveJobId?.(null)
    }
    setBusy(false)
    isSendingRef.current = false
    setMessages((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Generation stopped.',
      },
    ])
    toast('Generation stopped.', 'info')
  }

  const scrollToBottom = (smooth = true) => {
    requestAnimationFrame(() => {
      if (endRef.current) {
        endRef.current.scrollIntoView({
          behavior: smooth ? 'smooth' : 'auto',
          block: 'end',
        })
      }
    })
  }

  const toggleSidebar = () => {
    setSidebarOpen((prev) => {
      const next = !prev
      try {
        localStorage.setItem('sm_chat_sidebar_open', String(next))
      } catch {}
      return next
    })
  }

  const handleNewChat = () => {
    onClearPresentation?.()
    onConversationChange(null)
    setMessages([])
    setLoadingConversation(false)
    setConversationError(null)
    prevMsgCountRef.current = 0
    navigate('/chat')
  }

  useEffect(() => {
    prevConvIdRef.current = conversationId

    if (!conversationId) {
      // If we are actively sending, busy, or have active in-memory messages, DO NOT wipe them!
      if (isSendingRef.current || busy || messages.length > 0) {
        setLoadingConversation(false)
        setConversationError(null)
        return
      }
      setMessages([])
      setLoadingConversation(false)
      setConversationError(null)
      prevMsgCountRef.current = 0
      return
    }

    if (skipLoadFor.current === conversationId) {
      skipLoadFor.current = null
      setLoadingConversation(false)
      setConversationError(null)
      return
    }

    let isCurrent = true
    if (messages.length === 0) {
      setLoadingConversation(true)
    }
    setConversationError(null)

    api
      .getConversation(conversationId)
      .then((c) => {
        if (!isCurrent) return
        let msgs = c?.messages || []
        if (c?.active_job && c.active_job.status !== 'done' && c.active_job.status !== 'failed') {
          setActiveJobId?.(c.active_job.job_id)
          const activeJob = c.active_job
          const hasJobMsg = msgs.some((m) => m.job_id === activeJob.job_id)
          if (!hasJobMsg) {
            msgs = [
              ...msgs,
              {
                id: `job-${activeJob.job_id}`,
                role: 'assistant',
                content:
                  activeJob.kind === 'edit_presentation'
                    ? 'Updating presentation with requested changes...'
                    : 'Generating presentation...',
                job_id: activeJob.job_id,
                kind: activeJob.kind,
                generating: true,
              },
            ]
          } else {
            msgs = msgs.map((m) =>
              m.job_id === activeJob.job_id
                ? { ...m, generating: true, kind: activeJob.kind || m.kind }
                : m
            )
          }
        } else if ((!c?.active_job || c.active_job.status === 'done' || c.active_job.status === 'failed') && activeJobId) {
          setActiveJobId?.(null)
        }
        setMessages((prev) => {
          if (msgs.length === 0 && prev.length > 0) return prev
          return msgs
        })
        if (c?.active_presentation_id) {
          setActivePresentationId?.(c.active_presentation_id)
        }
        prevMsgCountRef.current = msgs.length
        setLoadingConversation(false)
        setConversationError(null)
        setTimeout(() => scrollToBottom(false), 50)
      })
      .catch((e) => {
        if (!isCurrent) return
        console.error('Failed to load conversation:', e)
        setLoadingConversation(false)
        setConversationError(e.message || 'Failed to load conversation')
        toast(e.message || 'Could not load conversation', 'error')
      })

    return () => {
      isCurrent = false
    }
  }, [conversationId])

  useEffect(() => {
    if (messages.length > 0 && messages.length !== prevMsgCountRef.current) {
      prevMsgCountRef.current = messages.length
      scrollToBottom(true)
    }
  }, [messages.length])

  useEffect(() => {
    const initPrompt = sessionStorage.getItem('initialPrompt')
    if (initPrompt) {
      sessionStorage.removeItem('initialPrompt')
      const initStyle = sessionStorage.getItem('initialStyle')
      const initDeepResearch = sessionStorage.getItem('initialDeepResearch') === '1'
      sessionStorage.removeItem('initialStyle')
      sessionStorage.removeItem('initialDeepResearch')
      send(initPrompt, { style: initStyle, deepResearch: initDeepResearch }, true)
    }
  }, [])

  const handleJobDone = async (result) => {
    setActiveJobId?.(null)
    notifyPresentationsUpdated?.()
    refreshHistory?.()
    const targetPid = result?.presentation_id
    if (targetPid) {
      setActivePresentationId?.(targetPid)
    }
    const currentConvId = conversationId || sessionStorage.getItem('sm_active_chat')
    if (currentConvId) {
      try {
        const c = await api.getConversation(currentConvId)
        if (c?.messages && c.messages.length > 0) {
          setMessages(c.messages)
          setTimeout(() => scrollToBottom(true), 100)
          return
        }
      } catch (err) {
        console.warn('Could not reload conversation after job completed:', err)
      }
    }
    setMessages((m) =>
      m.map((msg) =>
        msg.job_id
          ? {
              ...msg,
              generating: false,
              presentation_id: targetPid || msg.presentation_id,
              content: result?.summary || msg.content,
            }
          : msg
      )
    )
    setTimeout(() => scrollToBottom(true), 100)
  }

  const adopt = (id) => {
    if (id && id !== conversationId) {
      sessionStorage.setItem('sm_active_chat', id)
      localStorage.setItem('sm_active_chat', id)
      skipLoadFor.current = id
      onConversationChange(id)
    }
  }

  const send = async (text, options = {}, isInitial = false) => {
    if (isSendingRef.current || (!isInitial && (busy || Boolean(activeJobId))) || !text.trim()) return
    isSendingRef.current = true
    const cleanText = text.replace(/\[Style:[^\]]+\]/gi, '').replace(/\[Deep Research\]/gi, '').trim() || text
    setMessages((m) => {
      const hasOptimistic = m.some((msg) => msg.role === 'user' && msg.content === cleanText)
      if (hasOptimistic) return m
      return [...m, { id: crypto.randomUUID(), role: 'user', content: cleanText }]
    })
    setBusy(true)
    setTimeout(() => scrollToBottom(true), 50)
    abortControllerRef.current = new AbortController()
    try {
      const activePid = presentation?.id || activePresentationId
      const res = await api.chat(cleanText, conversationId, activePid, {
        ...options,
        signal: abortControllerRef.current.signal,
      })
      adopt(res.conversation_id)
      if (res.job_id) {
        setActiveJobId?.(res.job_id)
        setMessages((m) => [
          ...m,
          {
            id: `job-${res.job_id}`,
            role: 'assistant',
            content:
              res.reply ||
              (res.kind === 'edit_presentation'
                ? 'Updating presentation with requested changes...'
                : 'Generating your presentation...'),
            job_id: res.job_id,
            kind: res.kind || 'edit_presentation',
            generating: true,
          },
        ])
      } else {
        const nextPid = res.active_presentation_id || activePid || null
        setMessages((m) => [
          ...m,
          {
            id: res.message_id || crypto.randomUUID(),
            role: 'assistant',
            content: res.reply || '',
            citations: res.citations || [],
            tool_calls: res.tool_calls || [],
            presentation_id: nextPid,
          },
        ])
        if (nextPid) {
          setActivePresentationId?.(nextPid)
        }
        notifyPresentationsUpdated?.()
        refreshHistory?.()
      }
      setTimeout(() => scrollToBottom(true), 80)
    } catch (e) {
      if (e.name === 'CanceledError' || e.code === 'ERR_CANCELED' || e.message === 'canceled') {
        return
      }
      adopt(e.details?.conversation_id)
      let errorMessage = e.message
      if (e.code === 'rate_limit_exceeded') {
        errorMessage = 'The AI is currently rate-limited. Please wait a moment and try again.'
      } else if (e.code === 'ai_unavailable') {
        errorMessage = `AI service error: ${e.message}`
      } else if (e.code === 'ai_not_configured') {
        errorMessage = 'The AI service is not configured. Please contact the administrator.'
      } else if (e.status === 429) {
        errorMessage = 'Too many requests. Please wait a moment and try again.'
      } else if (e.status >= 500) {
        errorMessage = 'Server error. Please try again in a moment.'
      }
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: 'error', content: errorMessage }])
      toast(errorMessage, 'error')
      setTimeout(() => scrollToBottom(true), 80)
    } finally {
      setBusy(false)
      isSendingRef.current = false
      refreshHistory?.()
    }
  }

  const uploadFiles = async (files) => {
    for (const f of files) {
      try {
        await api.upload(f)
        toast(`${f.name} uploaded successfully.`, 'success')
      } catch (e) {
        toast(`${f.name}: ${e.message}`, 'error')
      }
    }
  }

  const handleUseTemplateCard = (themeName, promptSuggestion) => {
    send(`Create a presentation in the ${themeName} style: ${promptSuggestion}`)
  }

  return (
    <main
      className="home-shell relative flex min-h-screen min-w-0 flex-1 flex-col text-on-surface font-body-md antialiased overflow-x-hidden selection:bg-primary-container selection:text-white"
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        uploadFiles([...e.dataTransfer.files])
      }}
    >
      {/* Ambient Under-Glow & Micro Dotted Canvas */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute -top-40 -left-40 w-[650px] h-[650px] bg-[#F28C28]/15 rounded-full blur-[180px]" />
        <div className="absolute -top-40 -right-40 w-[650px] h-[650px] bg-[#DFA36D]/10 rounded-full blur-[190px]" />
        <div className="absolute inset-0 grid-pattern opacity-60" />
      </div>

      {/* Drag & Drop Upload Overlay */}
      {dragging && (
        <div className="fixed inset-6 z-50 flex flex-col items-center justify-center rounded-3xl bg-[#101114]/90 border-2 border-dashed border-[#F28C28] text-[#F28C28] backdrop-blur-xl">
          <span className="material-symbols-outlined text-5xl mb-3 animate-bounce">upload_file</span>
          <p className="text-xl font-headline-sm text-[#F4E6D3] font-medium">Drop reference documents here</p>
          <p className="mt-1 text-sm text-[#888A90]">Supported formats: PDF, DOCX, PPTX, TXT</p>
        </div>
      )}

      {/* Liquid Glass Left Sidebar for New Chat & History */}
      <ChatSidebar
        conversationId={conversationId}
        onSelectConversation={(id) => onConversationChange(id)}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={toggleSidebar}
      />

      {/* Main Viewport Container */}
      <div
        className={`relative z-10 flex-1 pt-20 sm:pt-24 pb-16 max-w-7xl mx-auto px-4 sm:px-6 md:px-12 w-full transition-all duration-300 ${
          sidebarOpen ? 'lg:pl-76' : ''
        }`}
      >
        {loadingConversation && messages.length === 0 ? (
          <div className="max-w-4xl mx-auto space-y-6 pb-48 pt-6">
            <div className="flex flex-col items-start max-w-[88%] w-full">
              <div className="flex items-center gap-1.5 mb-1 px-1">
                <div className="w-4 h-4 rounded-full bg-[#F28C28]/20 border border-[#F28C28]/35 flex items-center justify-center text-[#F28C28]">
                  <span className="material-symbols-outlined text-[11px]">auto_awesome</span>
                </div>
                <span className="font-label-sm text-[11px] text-[#F28C28] uppercase tracking-wider font-mono">
                  SlideMind AI
                </span>
              </div>
              <div className="w-full liquid-glass-card rounded-2xl rounded-tl-sm px-6 py-6 text-sm shadow-xl backdrop-blur-xl space-y-4">
                <div className="flex items-center gap-2.5 text-[#C5C0B8]">
                  <div className="w-4 h-4 rounded-full border-2 border-[#F28C28] border-t-transparent animate-spin" />
                  <span className="font-mono text-xs uppercase tracking-wider text-[#888A90]">
                    Loading conversation stream…
                  </span>
                </div>
                <div className="space-y-2.5 pt-1 animate-pulse">
                  <div className="h-3.5 bg-white/10 rounded-full w-3/4" />
                  <div className="h-3.5 bg-white/10 rounded-full w-5/6" />
                  <div className="h-3.5 bg-white/10 rounded-full w-1/2" />
                </div>
              </div>
            </div>
          </div>
        ) : conversationError ? (
          <div className="max-w-2xl mx-auto pt-16 pb-24 text-center">
            <div className="liquid-glass-card rounded-2xl border border-red-500/30 bg-red-500/10 p-8 shadow-2xl backdrop-blur-xl">
              <div className="w-12 h-12 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center mx-auto mb-4 text-red-400">
                <span className="material-symbols-outlined text-2xl">error_outline</span>
              </div>
              <h3 className="text-lg font-headline-sm font-semibold text-[#F4E6D3] mb-2">
                Conversation Unavailable
              </h3>
              <p className="text-sm text-[#C5C0B8] mb-6 max-w-md mx-auto">
                {conversationError}
              </p>
              <div className="flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={handleNewChat}
                  className="liquid-glass-btn-primary px-5 py-2 rounded-full text-[#101114] text-xs font-semibold cursor-pointer"
                >
                  Start New Chat
                </button>
                {conversationId && (
                  <button
                    type="button"
                    onClick={() => {
                      setConversationError(null)
                      setLoadingConversation(true)
                      api
                        .getConversation(conversationId)
                        .then((c) => {
                          setMessages(c?.messages || [])
                          setLoadingConversation(false)
                        })
                        .catch((err) => {
                          setConversationError(err.message || 'Failed to load conversation')
                          setLoadingConversation(false)
                        })
                    }}
                    className="liquid-glass-btn px-5 py-2 rounded-full text-[#F4E6D3] text-xs font-semibold cursor-pointer"
                  >
                    Retry
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div>
            {/* Hero Section */}
            <section className="home-hero text-center max-w-5xl mx-auto mb-6 sm:mb-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] backdrop-blur-md mb-2">
                <span className="material-symbols-outlined text-[#F28C28] text-sm">auto_awesome</span>
                <span className="font-label-sm text-[11px] uppercase tracking-widest text-[#888A90] font-mono">
                  Autonomous Architectural Deck Synthesis
                </span>
              </div>
              <h1 className="font-display-xl text-display-xl-mobile md:text-display-xl text-[#F4E6D3] font-normal tracking-tighter leading-[1.1]">
                Turn your ideas into<br />
                <span className="italic font-display-xl text-[#F28C28]">extraordinary</span> presentations.
              </h1>
              <p className="font-headline-sm text-sm sm:text-base text-[#C5C0B8] max-w-2xl mx-auto font-normal tracking-normal mt-2">
                Research deeply. Design intelligently. Present beautifully.
              </p>
            </section>

            {/* Central Prompt Composer */}
            <section className="max-w-4xl mx-auto mb-6 sm:mb-8">
              <ChatInput
                onSend={send}
                onStop={handleStopGeneration}
                busy={busy || Boolean(activeJobId)}
                onFiles={uploadFiles}
                disabled={busy || Boolean(activeJobId)}
                onOpenTemplates={onOpenTemplates}
                inConversation={false}
              />
            </section>

            {/* Editorial Spacing */}
            <div className="h-4 sm:h-6" />

            {/* Template Discovery Section */}
            <section>
              <div className="text-center max-w-2xl mx-auto mb-8 sm:mb-10 space-y-2">
                <h2 className="font-headline-md text-headline-md text-[#F4E6D3] font-normal tracking-tight">
                  Explore creative directions
                </h2>
                <p className="font-body-md text-body-md text-[#888A90]">
                  Curated architectural aesthetics for high-stakes narratives.
                </p>
              </div>

              {/* 6 Modern Aesthetic Direction Cards (1 col mobile, 2 col tablet, 3 col desktop) */}
              <div className="template-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
                {DESIGN_SYSTEMS.slice(0, 6).map((tmpl) => (
                  <ModernTemplateCard
                    key={tmpl.id}
                    tmpl={tmpl}
                    onInspect={onOpenTemplates}
                    onUse={() => handleUseTemplateCard(tmpl.name, tmpl.tagline)}
                  />
                ))}
              </div>
            </section>
          </div>
        ) : (
          /* Active Conversation Stream */
          <div className="max-w-4xl mx-auto space-y-6 pb-48">
            {messages.map((m, idx) => (
              <motion.div
                key={m.id || idx}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
              >
                {m.role === 'error' ? (
                  <div className="flex max-w-[85%] items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
                    <span className="material-symbols-outlined text-red-400">error</span>
                    <span>{m.content}</span>
                  </div>
                ) : m.role === 'user' ? (
                  <div className="flex flex-col items-end max-w-[85%]">
                    <div className="flex items-center gap-1.5 mb-1 px-1">
                      <span className="font-label-sm text-[11px] text-[#888A90] uppercase tracking-wider font-mono">You</span>
                      <div className="w-4 h-4 rounded-full bg-white/20 border border-white/30 flex items-center justify-center text-[9px] text-[#F4E6D3] font-medium">
                        U
                      </div>
                    </div>
                    <div className="rounded-2xl rounded-tr-sm px-5 py-3.5 bg-gradient-to-br from-white/[0.14] to-white/[0.06] border border-white/20 text-[#F4E6D3] shadow-[0_8px_24px_rgba(0,0,0,0.35)] backdrop-blur-xl">
                      <p className="whitespace-pre-wrap font-body-md text-sm text-[#F4E6D3] leading-relaxed selection:bg-white/30">
                        {m.content}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-start max-w-[88%] w-full">
                    <div className="flex items-center gap-1.5 mb-1 px-1">
                      <div className="w-4 h-4 rounded-full bg-[#F28C28]/20 border border-[#F28C28]/35 flex items-center justify-center text-[#F28C28]">
                        <span className="material-symbols-outlined text-[11px]">auto_awesome</span>
                      </div>
                      <span className="font-label-sm text-[11px] text-[#F28C28] uppercase tracking-wider font-mono">SlideMind AI</span>
                    </div>
                    <div className="w-full liquid-glass-card rounded-2xl rounded-tl-sm px-6 py-5 text-sm shadow-xl backdrop-blur-xl text-[#F4E6D3]">
                      {/* Tool execution badge cluster */}
                      {m.tool_calls?.length > 0 && (
                        <div className="mb-3.5 flex flex-wrap gap-1.5 border-b border-white/[0.06] pb-2.5">
                          {m.tool_calls.map((t, i) => (
                            <span
                              key={i}
                              title={`${t.duration_ms || 0} ms`}
                              className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-mono ${
                                t.status === 'success'
                                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/25'
                                  : 'bg-red-500/15 text-red-300 border border-red-500/25'
                              }`}
                            >
                              <span className="material-symbols-outlined text-xs">
                                {t.status === 'success' ? 'check_circle' : 'cancel'}
                              </span>
                              <span>{(t.name || 'tool').replace(/_/g, ' ')}</span>
                            </span>
                          ))}
                        </div>
                      )}

                      <ErrorBoundary>
                        <ReactMarkdown className="prose prose-invert prose-sm max-w-none leading-relaxed text-[#F4E6D3]">
                          {m.content || ''}
                        </ReactMarkdown>

                        {/* Citations */}
                        {m.citations?.length > 0 && (
                          <div className="mt-3.5 flex flex-wrap gap-1.5 border-t border-white/[0.06] pt-2.5">
                            {m.citations.map((c) => (
                              <button
                                key={c.n}
                                onClick={() => setCitation(c)}
                                className="glass-pill rounded-full px-2.5 py-0.5 text-[11px] text-[#F28C28] hover:text-[#DFA36D] transition-colors cursor-pointer"
                              >
                                [{c.n}] {c.filename}
                                {c.page_number ? ` p.${c.page_number}` : ''}
                              </button>
                            ))}
                          </div>
                        )}

                        {/* In-Flight Background Generation / Edit Progress */}
                        {m.job_id && (m.generating || (activeJobId && activeJobId === m.job_id)) && (
                          <div className="mt-4 pt-4 border-t border-white/[0.08]">
                            <JobProgress
                              jobId={m.job_id}
                              kind={m.kind}
                              onDone={handleJobDone}
                              onRetry={() => {
                                send(
                                  m.kind === 'edit_presentation'
                                    ? 'Please retry applying these changes.'
                                    : 'Please retry generating this presentation.'
                                )
                              }}
                            />
                          </div>
                        )}

                        {/* Interactive In-Chat Slide Deck Canvas */}
                        {m.presentation_id && (() => {
                          let lastIdxForPres = -1
                          for (let i = messages.length - 1; i >= 0; i--) {
                            if (messages[i]?.presentation_id === m.presentation_id) {
                              lastIdxForPres = i
                              break
                            }
                          }
                          const isLatestForDeck = lastIdxForPres === idx

                          if (!isLatestForDeck) {
                            return (
                              <div className="mt-3.5 flex items-center justify-between rounded-xl border border-white/[0.08] bg-white/[0.02] px-3.5 py-2 text-xs text-[#888A90] backdrop-blur-md">
                                <div className="flex items-center gap-2">
                                  <span className="material-symbols-outlined text-sm text-[#F28C28]">history</span>
                                  <span>Previous presentation revision</span>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => scrollToBottom(true)}
                                  className="text-xs text-[#F28C28] hover:text-[#DFA36D] transition-colors cursor-pointer flex items-center gap-1 font-medium"
                                >
                                  <span>View latest slides</span>
                                  <span className="material-symbols-outlined text-xs">arrow_downward</span>
                                </button>
                              </div>
                            )
                          }

                          return (
                            <ErrorBoundary>
                              <ChatDeckPreview
                                presentationId={m.presentation_id}
                                onOpenPresent={(pres, slideIdx) =>
                                  setPresenterDeck({ presentation: pres, slideIndex: slideIdx })
                                }
                                onOpenWorkspace={(pid) => navigate(`/presentations/${pid}`)}
                                onQuickPrompt={(promptText) => send(promptText)}
                              />
                            </ErrorBoundary>
                          )
                        })()}
                      </ErrorBoundary>
                    </div>
                  </div>
                )}
              </motion.div>
            ))}

            {busy && (
              <div className="flex flex-col items-start max-w-[88%] w-full">
                <div className="flex items-center gap-1.5 mb-1 px-1">
                  <div className="w-4 h-4 rounded-full bg-[#F28C28]/20 border border-[#F28C28]/35 flex items-center justify-center text-[#F28C28]">
                    <span className="material-symbols-outlined text-[11px]">auto_awesome</span>
                  </div>
                  <span className="font-label-sm text-[11px] text-[#F28C28] uppercase tracking-wider font-mono">SlideMind AI</span>
                </div>
                <div className="liquid-glass-card rounded-2xl rounded-tl-sm px-5 py-3 flex items-center gap-2 text-[#888A90]">
                  <span className="material-symbols-outlined animate-spin text-[#F28C28]">autorenew</span>
                  <span className="text-xs font-label-md text-[#C5C0B8]">Synthesizing architectural slide specification…</span>
                </div>
              </div>
            )}

            <div ref={endRef} className="h-6" />
          </div>
        )}

        {/* Fixed Docked Prompt Composer for Active Conversation / Loading State */}
        {(messages.length > 0 || Boolean(conversationId) || loadingConversation) && (
          <div
            className={`fixed bottom-6 left-1/2 w-[92%] max-w-4xl z-40 transition-all duration-300 ${
              sidebarOpen
                ? 'lg:left-[calc(50%+9.5rem)] -translate-x-1/2'
                : '-translate-x-1/2'
            }`}
          >
            {presentation && (
              <div className="mb-2 flex items-center justify-between rounded-xl border border-white/10 bg-zinc-900/95 backdrop-blur-xl px-4 py-1.5 text-xs text-outline shadow-xl">
                <span className="truncate text-white/80">
                  Context: <strong className="text-white font-medium">{presentation.title}</strong>
                </span>
                <button
                  onClick={onClearPresentation}
                  className="text-white/60 hover:text-white hover:underline text-[11px] ml-3 transition-colors cursor-pointer"
                >
                  Clear
                </button>
              </div>
            )}
            <ChatInput
              onSend={send}
              onStop={handleStopGeneration}
              busy={busy || Boolean(activeJobId)}
              onFiles={uploadFiles}
              disabled={busy || Boolean(activeJobId) || loadingConversation}
              onOpenTemplates={onOpenTemplates}
              inConversation={true}
            />
          </div>
        )}

        {/* Minimal Editorial Footer - Only on Empty Hero Page */}
        {!loadingConversation && !conversationError && !conversationId && messages.length === 0 && (
          <footer className="border-t border-outline-variant/20 bg-surface-container-lowest text-primary py-8 mt-24">
            <div className="flex flex-col md:flex-row justify-between items-center max-w-7xl mx-auto px-2 md:px-6 w-full gap-4">
              <div className="font-label-sm text-label-sm text-outline text-center md:text-left">
                © 2025 SlideMind AI Studio. Architectural presentation intelligence. Model v4.2.
              </div>
              <div className="flex items-center gap-6 font-label-sm text-label-sm text-outline">
                <a className="hover:text-on-surface transition-colors duration-200" href="#">
                  Legal & Privacy
                </a>
                <a className="hover:text-on-surface transition-colors duration-200" href="#">
                  System Telemetry
                </a>
                <button
                  type="button"
                  onClick={() => setCommandPaletteOpen?.(true)}
                  className="hover:text-[#F4E6D3] transition-colors duration-200 font-mono cursor-pointer"
                >
                  Shortcuts [⌘K]
                </button>
                <a className="hover:text-on-surface transition-colors duration-200" href="#">
                  Documentation
                </a>
              </div>
            </div>
          </footer>
        )}
      </div>

      {/* Citation Detail Modal */}
      {citation && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          onClick={() => setCitation(null)}
        >
          <div
            className="rounded-2xl bg-[#17191E] border border-white/[0.14] max-h-[80vh] w-full max-w-xl overflow-y-auto p-6 shadow-2xl backdrop-blur-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h3 className="text-base font-headline-sm font-medium text-[#F4E6D3]">
                  {citation.filename}
                </h3>
                <p className="mt-0.5 text-xs text-[#888A90]">
                  {citation.page_number ? `Page ${citation.page_number}` : 'Reference'}
                  {citation.section_heading && ` · ${citation.section_heading}`}
                </p>
              </div>
              <button
                onClick={() => setCitation(null)}
                className="rounded-lg p-1.5 text-[#888A90] hover:text-[#F4E6D3]"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>
            <div className="rounded-xl bg-[#1E2026] border border-white/[0.08] p-4 text-xs leading-relaxed text-[#C5C0B8] font-mono">
              {citation.passage}
            </div>
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setCitation(null)}
                className="liquid-glass-btn rounded-full px-4 py-1.5 text-xs font-semibold text-[#F4E6D3] cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Presenter Mode */}
      {presenterDeck && (
        <PresenterModal
          presentation={presenterDeck.presentation}
          initialSlideIndex={presenterDeck.slideIndex || 0}
          onClose={() => setPresenterDeck(null)}
        />
      )}
    </main>
  )
}

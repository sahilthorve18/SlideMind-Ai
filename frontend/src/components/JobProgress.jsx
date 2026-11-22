import { useEffect, useRef, useState } from 'react'
import { AlertCircle, CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { api } from '../services/api'

export default function JobProgress({ jobId, kind, onDone, onFailed, onRetry }) {
  const [job, setJob] = useState(null)
  const [netError, setNetError] = useState(false)
  const doneRef = useRef(false)

  useEffect(() => {
    let alive = true
    let eventSource = null
    let pollTimer = null

    const token = localStorage.getItem('sm_token') || ''
    const apiBase = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
    const streamUrl = `${apiBase}/api/presentation/status/stream?job_id=${encodeURIComponent(jobId)}&token=${encodeURIComponent(token)}`

    const handleUpdate = (j) => {
      if (!alive || !j) return
      setJob(j)
      setNetError(false)
      if (j.status === 'done' && !doneRef.current) {
        doneRef.current = true
        if (eventSource) eventSource.close()
        return onDone?.(j.result)
      }
      if (j.status === 'failed') {
        if (eventSource) eventSource.close()
        onFailed?.(j.error)
      }
    }

    const startPolling = () => {
      let failCount = 0
      const poll = async () => {
        try {
          const j = await api.jobStatus(jobId)
          if (!alive) return
          handleUpdate(j)
          if (j.status !== 'done' && j.status !== 'failed') {
            pollTimer = setTimeout(poll, 1500)
          }
        } catch (err) {
          if (!alive) return
          failCount++
          if (err?.status === 404 || failCount > 6) {
            onFailed?.('Job completed or unavailable.')
            return
          }
          setNetError(true)
          pollTimer = setTimeout(poll, 2500)
        }
      }
      poll()
    }

    // Try Server-Sent Events (SSE) for instantaneous, zero-latency progress updates
    if (typeof EventSource !== 'undefined' && token) {
      try {
        eventSource = new EventSource(streamUrl)
        eventSource.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data)
            handleUpdate(data)
          } catch (err) {
            console.error('SSE parse error:', err)
          }
        }
        eventSource.onerror = () => {
          if (eventSource) {
            eventSource.close()
            eventSource = null
          }
          if (alive && !doneRef.current) {
            startPolling()
          }
        }
      } catch {
        startPolling()
      }
    } else {
      startPolling()
    }

    return () => {
      alive = false
      if (eventSource) eventSource.close()
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [jobId])

  const failed = job?.status === 'failed'
  const isEdit = (job?.kind || kind) === 'edit_presentation'
  return (
    <div className="mx-auto w-full max-w-xl space-y-4 p-4">
      <h2 className="text-xl font-semibold text-[#F4E6D3]">
        {failed
          ? (isEdit ? 'Failed to apply changes' : 'Generation failed')
          : (isEdit ? 'Updating your presentation' : 'Generating your presentation')}
      </h2>
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.08]">
        <div
          className={`h-full transition-all duration-500 ${failed ? 'bg-red-500' : 'bg-[#F28C28]'}`}
          style={{ width: `${job?.progress ?? (isEdit ? 15 : 2)}%` }}
        />
      </div>
      <div className="text-sm text-[#888A90] font-mono">
        {job ? `${job.progress}%` : (isEdit ? 'Analyzing requested changes…' : 'Starting…')}
        {netError && ' · connection problem, retrying…'}
      </div>
      <ul className="space-y-1.5 text-sm text-[#C5C0B8]">
        {(job?.log || []).map((e, i) => (
          <li key={i} className="flex items-center gap-2">
            {e.status === 'success' ? (
              <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
            ) : (
              <XCircle size={14} className="text-red-400 shrink-0" />
            )}
            <span className="text-[#F4E6D3]">{e.label}</span>
            {e.status !== 'success' && (
              <span className="text-xs text-[#888A90]">(skipped or failed; the assistant adapted)</span>
            )}
          </li>
        ))}
        {!failed && job && (
          <li className="flex items-center gap-2 text-[#F28C28]">
            <Loader2 size={14} className="animate-spin shrink-0" />
            <span>{isEdit ? 'Applying edits to slides…' : 'Working…'}</span>
          </li>
        )}
      </ul>
      {failed && (
        <div className="space-y-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          <div className="flex items-start gap-2">
            <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-400" />
            <span>{job.error || 'Operation failed'}</span>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="rounded-lg bg-[#F28C28] px-3 py-1.5 text-[#101114] text-xs font-semibold cursor-pointer hover:bg-[#F28C28]/90 transition"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  )
}

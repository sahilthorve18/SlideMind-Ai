import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  Award,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Loader2,
  Mic,
  MicOff,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Volume2,
} from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'
import SlideView from './SlideView'

export default function RehearsalView({ presentation, onBackToSlides }) {
  const { toast } = useApp()
  const slides = presentation?.slides || []
  const [slideIdx, setSlideIdx] = useState(0)
  const [timerRunning, setTimerRunning] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [transcript, setTranscript] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [slideResult, setSlideResult] = useState(null)
  const [deckResult, setDeckResult] = useState(null)
  const [slideRuns, setSlideRuns] = useState({}) // { slidePos: { transcript, duration_seconds } }

  const recognitionRef = useRef(null)
  const timerRef = useRef(null)

  const currentSlide = slides[slideIdx]
  const theme = presentation?.themes?.[presentation?.settings?.theme]

  // Setup SpeechRecognition if supported
  useEffect(() => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRec) {
      const rec = new SpeechRec()
      rec.continuous = true
      rec.interimResults = true
      rec.lang = presentation?.settings?.language?.includes('English') ? 'en-US' : 'en-US'

      rec.onresult = (evt) => {
        let full = ''
        for (let i = 0; i < evt.results.length; ++i) {
          full += evt.results[i][0].transcript + ' '
        }
        setTranscript(full.trim())
      }

      rec.onerror = (e) => {
        if (e.error !== 'no-speech') {
          console.warn('Speech recognition error:', e.error)
        }
      }

      recognitionRef.current = rec
    }
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch {}
      }
    }
  }, [presentation])

  // Stopwatch timer
  useEffect(() => {
    if (timerRunning) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((s) => s + 1)
      }, 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [timerRunning])

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      toast('Speech recognition is not supported in this browser. You can type or paste your spoken words directly.', 'info')
      setTimerRunning(!timerRunning)
      return
    }

    if (isRecording) {
      try {
        recognitionRef.current.stop()
      } catch {}
      setIsRecording(false)
      setTimerRunning(false)
    } else {
      try {
        recognitionRef.current.start()
        setIsRecording(true)
        setTimerRunning(true)
      } catch (err) {
        toast('Could not start microphone: ' + err.message, 'error')
      }
    }
  }

  const resetRun = () => {
    setTimerRunning(false)
    setElapsedSeconds(0)
    setTranscript('')
    setSlideResult(null)
    if (isRecording && recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {}
      setIsRecording(false)
    }
  }

  const analyzeCurrentSlide = async () => {
    if (!transcript.trim()) {
      toast('Please speak or type your practice delivery first.', 'info')
      return
    }
    setAnalyzing(true)
    try {
      const dur = Math.max(5, elapsedSeconds)
      const res = await api.practiceSlide({
        presentation_id: presentation.id,
        slide_position: currentSlide.position,
        transcript: transcript.trim(),
        duration_seconds: dur,
      })
      setSlideResult(res)
      setSlideRuns((prev) => ({
        ...prev,
        [currentSlide.position]: {
          slide_position: currentSlide.position,
          transcript: transcript.trim(),
          duration_seconds: dur,
        },
      }))
      toast('Analysis complete for Slide ' + currentSlide.position, 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setAnalyzing(false)
    }
  }

  const completeDeckRehearsal = async () => {
    const runsList = Object.values(slideRuns)
    if (runsList.length === 0 && transcript.trim()) {
      runsList.push({
        slide_position: currentSlide.position,
        transcript: transcript.trim(),
        duration_seconds: Math.max(5, elapsedSeconds),
      })
    }
    if (runsList.length === 0) {
      toast('Rehearse at least one slide before generating the deck scorecard.', 'info')
      return
    }
    setAnalyzing(true)
    try {
      const res = await api.practiceDeck({
        presentation_id: presentation.id,
        runs: runsList,
      })
      setDeckResult(res)
      toast('Deck Rehearsal Scorecard generated!', 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setAnalyzing(false)
    }
  }

  const formatTimer = (sec) => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const bullets = currentSlide?.content?.bullets || []

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/10 text-brand-600 dark:text-brand-400">
            <Volume2 size={20} />
          </div>
          <div>
            <h2 className="text-base font-bold">Presenter Rehearsal Coach</h2>
            <p className="text-xs text-slate-500">
              Slide {slideIdx + 1} of {slides.length} · Practice verbal delivery with live timing and filler analysis
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-1.5 font-mono text-sm font-bold text-slate-800 dark:bg-slate-800 dark:text-slate-200">
            <Clock size={16} className={timerRunning ? 'animate-pulse text-brand-500' : 'text-slate-400'} />
            {formatTimer(elapsedSeconds)}
          </div>
          <button
            onClick={() => setTimerRunning(!timerRunning)}
            className="rounded-lg border border-slate-300 p-2 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            title={timerRunning ? 'Pause timer' : 'Start timer'}
          >
            {timerRunning ? <Pause size={15} /> : <Play size={15} />}
          </button>
          <button
            onClick={resetRun}
            className="rounded-lg border border-slate-300 p-2 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            title="Reset slide practice"
          >
            <RotateCcw size={15} />
          </button>
          <button
            onClick={completeDeckRehearsal}
            disabled={analyzing}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-brand-500 disabled:opacity-50"
          >
            <Award size={14} /> Full Deck Scorecard
          </button>
        </div>
      </div>

      {/* Main Practice Workspace */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Visual Slide & Teleprompter */}
        <div className="space-y-4 lg:col-span-7">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            {currentSlide && <SlideView slide={currentSlide} theme={theme} first={slideIdx === 0} />}
          </div>

          {/* Teleprompter Notes */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Speaker Notes Teleprompter
              </span>
              <span className="text-[11px] text-slate-400">Target Pace: ~130 words/min</span>
            </div>
            {currentSlide?.speaker_notes ? (
              <p className="max-h-48 overflow-y-auto whitespace-pre-wrap text-base font-medium leading-relaxed text-slate-800 dark:text-slate-100">
                {currentSlide.speaker_notes}
              </p>
            ) : (
              <p className="text-sm italic text-slate-400">
                No speaker notes written for this slide. Use the AI Auto-Fix in the Intelligence tab to generate notes.
              </p>
            )}
          </div>

          {/* Slide Navigation Buttons */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => {
                if (slideIdx > 0) {
                  setSlideIdx(slideIdx - 1)
                  resetRun()
                }
              }}
              disabled={slideIdx === 0}
              className="flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              <ChevronLeft size={16} /> Previous Slide
            </button>
            <span className="text-xs text-slate-500">
              Slide {slideIdx + 1} of {slides.length}
            </span>
            <button
              onClick={() => {
                if (slideIdx < slides.length - 1) {
                  setSlideIdx(slideIdx + 1)
                  resetRun()
                }
              }}
              disabled={slideIdx === slides.length - 1}
              className="flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Next Slide <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Right Column: Audio Recording / Practice Input & Real-Time Feedback */}
        <div className="space-y-4 lg:col-span-5">
          {/* Practice Input Box */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Practice Transcript
              </span>
              <button
                onClick={toggleRecording}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition ${
                  isRecording
                    ? 'animate-pulse bg-rose-500 text-white shadow-rose-500/20'
                    : 'border border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800'
                }`}
              >
                {isRecording ? <MicOff size={13} /> : <Mic size={13} />}
                {isRecording ? 'Listening...' : 'Voice Dictate'}
              </button>
            </div>

            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Start voice dictation or type the words you plan to say for this slide..."
              rows={5}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm focus:border-brand-500 focus:bg-white focus:outline-none dark:border-slate-800 dark:bg-slate-950 dark:focus:bg-slate-900"
            />

            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {transcript.split(/\s+/).filter(Boolean).length} words spoken
              </span>
              <button
                onClick={analyzeCurrentSlide}
                disabled={analyzing || !transcript.trim()}
                className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow hover:bg-brand-500 disabled:opacity-50"
              >
                {analyzing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                Analyze Slide Run
              </button>
            </div>
          </div>

          {/* Slide Run Feedback Scorecard */}
          {slideResult && (
            <div className="space-y-3 rounded-2xl border border-brand-500/20 bg-gradient-to-br from-white to-slate-50 p-5 shadow-sm dark:from-slate-900 dark:to-slate-950">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400">
                  Slide Delivery Score
                </span>
                <span className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  {slideResult.overall_score}/100
                </span>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl border border-slate-200 bg-white p-2.5 dark:border-slate-800 dark:bg-slate-900">
                  <div className="text-[10px] text-slate-400">Speaking Pace</div>
                  <div className="text-sm font-bold text-slate-800 dark:text-slate-200">{slideResult.wpm} WPM</div>
                  <div className="text-[10px] capitalize text-brand-600 dark:text-brand-400">
                    {slideResult.pace_status.replace('_', ' ')}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-2.5 dark:border-slate-800 dark:bg-slate-900">
                  <div className="text-[10px] text-slate-400">Filler Words</div>
                  <div className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    {slideResult.total_fillers}
                  </div>
                  <div className="text-[10px] text-slate-500">{slideResult.filler_rate_pct}% rate</div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-2.5 dark:border-slate-800 dark:bg-slate-900">
                  <div className="text-[10px] text-slate-400">Point Coverage</div>
                  <div className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    {slideResult.coverage_pct}%
                  </div>
                  <div className="text-[10px] text-emerald-600 dark:text-emerald-400">Key concepts</div>
                </div>
              </div>

              {/* Coaching Feedback Tips */}
              <div className="space-y-1.5 pt-2">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Coach Guidance</div>
                {slideResult.coaching_tips?.map((tip, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-slate-700 dark:text-slate-300">
                    <span className="text-brand-500">•</span>
                    <span>{tip}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full Deck Rehearsal Scorecard */}
          {deckResult && (
            <div className="space-y-3 rounded-2xl border border-emerald-500/30 bg-emerald-50/40 p-5 dark:bg-emerald-950/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Award size={18} className="text-emerald-500" />
                  <span className="text-sm font-bold text-emerald-900 dark:text-emerald-200">
                    Full Deck Scorecard
                  </span>
                </div>
                <div className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-bold text-emerald-700 dark:text-emerald-300">
                  Grade {deckResult.grade} ({deckResult.overall_score}/100)
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-lg bg-white/80 p-2 dark:bg-slate-900">
                  <div className="text-[10px] text-slate-400">Total Duration</div>
                  <div className="font-bold">{deckResult.total_minutes} min</div>
                </div>
                <div className="rounded-lg bg-white/80 p-2 dark:bg-slate-900">
                  <div className="text-[10px] text-slate-400">Average Pace</div>
                  <div className="font-bold">{deckResult.overall_wpm} WPM</div>
                </div>
                <div className="rounded-lg bg-white/80 p-2 dark:bg-slate-900">
                  <div className="text-[10px] text-slate-400">Total Fillers</div>
                  <div className="font-bold">{deckResult.total_fillers}</div>
                </div>
              </div>

              {deckResult.summary_tips?.length > 0 && (
                <div className="space-y-1 text-xs text-emerald-950 dark:text-emerald-200">
                  {deckResult.summary_tips.map((tip, idx) => (
                    <div key={idx} className="flex items-start gap-1.5">
                      <span>✓</span>
                      <span>{tip}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

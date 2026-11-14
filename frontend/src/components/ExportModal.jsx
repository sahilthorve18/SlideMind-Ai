import { useState } from 'react'
import {
  X,
  Download,
  FileText,
  Presentation,
  Check,
  Sparkles,
  Sliders,
  Layers,
  Monitor,
} from 'lucide-react'
import { api } from '../services/api'
import { triggerFileDownload } from '../utils/download'
import { useApp } from '../context/AppContext'

export default function ExportModal({
  isOpen,
  onClose,
  presentation,
}) {
  const { toast } = useApp()
  const [format, setFormat] = useState('pptx') // 'pptx' | 'pdf'
  const [aspectRatio, setAspectRatio] = useState('16:9') // '16:9' | '4:3'
  const [includeNotes, setIncludeNotes] = useState(true)
  const [includeVisuals, setIncludeVisuals] = useState(true)
  const [downloading, setDownloading] = useState(false)

  if (!isOpen || !presentation) return null

  const handleDownload = async () => {
    setDownloading(true)
    try {
      toast(`Generating high-fidelity ${format.toUpperCase()} export...`, 'info')
      let blob
      try {
        blob = await api.downloadPresentation(presentation.id, format)
      } catch {
        blob = await api.exportPresentation(presentation.id, format)
      }
      triggerFileDownload(blob, presentation.title || 'presentation', format)
      toast(`${format.toUpperCase()} download ready!`, 'success')
      onClose()
    } catch (err) {
      toast(err.message || 'Export failed. Please try again.', 'error')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-2xl liquid-glass-modal border border-white/[0.14] shadow-[0_24px_60px_rgba(0,0,0,0.85)] animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/[0.08] px-6 py-4 bg-[#17191E]/60">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#F28C28]/15 border border-[#F28C28]/30 text-[#F28C28]">
              <Download size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-[#F4E6D3]">Export Presentation</h3>
              <p className="text-xs text-[#888A90] truncate max-w-xs">
                {presentation.title || 'Untitled Presentation'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/[0.08] cursor-pointer transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Format Selection */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-[#C5C0B8] mb-2.5">
              Export Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormat('pptx')}
                className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                  format === 'pptx'
                    ? 'border-[#F28C28]/50 bg-[#F28C28]/12 text-[#F4E6D3] shadow-sm'
                    : 'border-white/[0.10] bg-white/[0.03] text-[#C5C0B8] hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <Presentation size={16} className={format === 'pptx' ? 'text-[#F28C28]' : 'text-[#888A90]'} />
                    <span className="text-sm font-semibold text-[#F4E6D3]">PowerPoint (.pptx)</span>
                  </div>
                  {format === 'pptx' && <Check size={14} className="text-[#F28C28]" />}
                </div>
                <p className="text-[11px] text-[#888A90] leading-tight">
                  Fully editable vector shapes, native text, and layouts. Compatible with Google Slides.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setFormat('pdf')}
                className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                  format === 'pdf'
                    ? 'border-[#F28C28]/50 bg-[#F28C28]/12 text-[#F4E6D3] shadow-sm'
                    : 'border-white/[0.10] bg-white/[0.03] text-[#C5C0B8] hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <FileText size={16} className={format === 'pdf' ? 'text-[#F28C28]' : 'text-[#888A90]'} />
                    <span className="text-sm font-semibold text-[#F4E6D3]">PDF Document</span>
                  </div>
                  {format === 'pdf' && <Check size={14} className="text-[#F28C28]" />}
                </div>
                <p className="text-[11px] text-[#888A90] leading-tight">
                  High-fidelity fixed document for pitching, investor reviews, and offline viewing.
                </p>
              </button>
            </div>
          </div>

          {/* Aspect Ratio Selection */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-[#C5C0B8] mb-2.5">
              Canvas Dimension
            </label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: '16:9', label: '16:9 Widescreen', desc: 'Modern Displays & TV (1920×1080)' },
                { id: '4:3', label: '4:3 Standard', desc: 'Conference Hall Projectors' },
              ].map((ar) => (
                <button
                  key={ar.id}
                  type="button"
                  onClick={() => setAspectRatio(ar.id)}
                  className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                    aspectRatio === ar.id
                      ? 'border-[#F28C28]/50 bg-[#F28C28]/10 text-[#F4E6D3]'
                      : 'border-white/[0.10] bg-white/[0.03] text-[#C5C0B8] hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#F4E6D3]">{ar.label}</span>
                    {aspectRatio === ar.id && <Check size={13} className="text-[#F28C28]" />}
                  </div>
                  <span className="block text-[10px] text-[#888A90] mt-0.5">{ar.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Toggles */}
          <div className="space-y-2 pt-1 border-t border-white/[0.08]">
            <label className="flex items-center justify-between p-2 rounded-xl hover:bg-white/[0.03] cursor-pointer">
              <span className="text-xs text-[#F4E6D3] font-medium">Include Speaker Notes & Key Cues</span>
              <input
                type="checkbox"
                checked={includeNotes}
                onChange={(e) => setIncludeNotes(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/10 text-[#F28C28] focus:ring-0 cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between p-2 rounded-xl hover:bg-white/[0.03] cursor-pointer">
              <span className="text-xs text-[#F4E6D3] font-medium">Render High-Resolution Visual Assets</span>
              <input
                type="checkbox"
                checked={includeVisuals}
                onChange={(e) => setIncludeVisuals(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/10 text-[#F28C28] focus:ring-0 cursor-pointer"
              />
            </label>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-white/[0.08] bg-[#101114]/70 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            disabled={downloading}
            className="liquid-glass-btn px-4 py-2 rounded-full text-xs font-semibold text-[#C5C0B8] hover:text-[#F4E6D3] cursor-pointer"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="liquid-glass-btn-primary flex items-center gap-2 px-5 py-2 rounded-full text-xs font-semibold text-[#101114] cursor-pointer transition-all active:scale-95 disabled:opacity-50"
          >
            {downloading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-[#101114] border-t-transparent rounded-full animate-spin" />
                <span>Exporting Deck…</span>
              </>
            ) : (
              <>
                <Download size={14} />
                <span>Download {format.toUpperCase()}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

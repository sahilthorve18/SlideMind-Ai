import { useEffect, useRef, useState } from 'react'
import { FileText, Loader2, Trash2, Upload, X } from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'

const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)

export default function DocumentsPanel({ onClose }) {
  const { toast } = useApp()
  const [docs, setDocs] = useState(null)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)

  const load = () =>
    api
      .documents()
      .then(setDocs)
      .catch((e) => {
        setDocs([])
        toast(e.message, 'error')
      })

  useEffect(() => {
    load()
  }, [])

  const upload = async (files) => {
    setUploading(true)
    for (const f of files) {
      try {
        const d = await api.upload(f)
        toast(d.duplicate ? `${f.name} was already indexed.` : `${f.name} indexed successfully.`, 'success')
      } catch (e) {
        toast(`${f.name}: ${e.message}`, 'error')
      }
    }
    setUploading(false)
    load()
  }

  const remove = async (id) => {
    try {
      await api.deleteDocument(id)
      load()
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl liquid-glass-modal p-6 shadow-2xl border border-white/[0.14]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#F28C28]/15 border border-[#F28C28]/30 text-[#F28C28]">
              <FileText size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#F4E6D3]">Uploaded Documents</h2>
              <p className="text-xs text-[#888A90]">Reference material for AI research and slide citations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1.5 text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/[0.08] cursor-pointer transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <input
          ref={fileRef}
          type="file"
          hidden
          multiple
          accept=".pdf,.docx,.pptx,.txt"
          onChange={(e) => {
            upload([...e.target.files])
            e.target.value = ''
          }}
        />

        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/[0.14] bg-white/[0.03] py-3 text-xs font-semibold text-[#F4E6D3] hover:border-[#F28C28]/60 hover:bg-[#F28C28]/05 disabled:opacity-60 transition cursor-pointer"
        >
          {uploading ? (
            <>
              <Loader2 size={15} className="animate-spin text-[#F28C28]" />
              <span>Indexing documents…</span>
            </>
          ) : (
            <>
              <Upload size={15} className="text-[#F28C28]" />
              <span>Upload PDF, DOCX, PPTX or TXT</span>
            </>
          )}
        </button>

        {docs === null && <p className="text-center py-4 text-xs text-[#888A90]">Loading documents…</p>}
        {docs?.length === 0 && (
          <p className="py-8 text-center text-xs text-[#888A90]">
            No documents indexed yet. Upload whitepapers, briefs, or meeting notes to ground your presentations.
          </p>
        )}

        <ul className="space-y-2">
          {docs?.map((d) => (
            <li
              key={d.id}
              className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.03] p-3 text-xs transition-colors hover:border-white/[0.14]"
            >
              <FileText size={18} className="shrink-0 text-[#F28C28]" />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-[#F4E6D3]">{d.filename}</div>
                <div className="text-[11px] text-[#888A90]">
                  {d.file_type.toUpperCase()} · {kb(d.size_bytes)}
                  {d.page_count ? ` · ${d.page_count} pages` : ''}
                </div>
              </div>
              <button
                onClick={() => remove(d.id)}
                aria-label={`Delete ${d.filename}`}
                className="rounded-lg p-1 text-[#888A90] hover:text-red-400 hover:bg-red-500/10 cursor-pointer transition-colors"
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

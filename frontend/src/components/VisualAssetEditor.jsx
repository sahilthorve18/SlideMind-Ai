import { useState, useRef } from 'react'
import {
  Image as ImageIcon,
  Sparkles,
  Upload,
  RefreshCw,
  Trash2,
  GitCommit,
  Check,
  X,
  Loader2,
  ExternalLink,
  Shield,
  Layers,
} from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'

export default function VisualAssetEditor({
  presentationId,
  slide,
  onSlideUpdated,
}) {
  const { toast } = useApp()
  const [loading, setLoading] = useState(false)
  const [showCandidates, setShowCandidates] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [brief, setBrief] = useState(null)
  const [userAssets, setUserAssets] = useState([])
  const [showUserLibrary, setShowUserLibrary] = useState(false)
  const fileInputRef = useRef(null)

  const currentImage = slide?.content?.image

  // 1. Find a Better Visual (Queries Visual Intelligence Engine)
  const handleFindBetterVisual = async () => {
    setLoading(true)
    setShowCandidates(true)
    setShowUserLibrary(false)
    try {
      const res = await api.getVisualCandidates(presentationId, slide.position)
      setCandidates(res.candidates || [])
      setBrief(res.brief || null)
    } catch (err) {
      toast(err.message || 'Failed to retrieve visual candidates.', 'error')
      setShowCandidates(false)
    } finally {
      setLoading(false)
    }
  }

  // 2. Select Candidate / Replace Visual
  const handleSelectCandidate = async (candidate) => {
    setLoading(true)
    try {
      const formattedImage = {
        url: candidate.image_url,
        thumb_url: candidate.thumb_url,
        title: candidate.title,
        description: candidate.description,
        source: candidate.source,
        source_page: candidate.source_page,
        artist: candidate.artist,
        artist_url: candidate.artist_url,
        license: candidate.license,
        license_url: candidate.license_url,
        dimensions: {
          width: candidate.width,
          height: candidate.height,
          aspect_ratio: candidate.aspect_ratio,
        },
        relevance_score: candidate.score,
        alt: candidate.title || slide.title,
      }
      await api.selectSlideVisual(presentationId, slide.position, formattedImage)
      toast('Slide visual updated successfully!', 'success')
      setShowCandidates(false)
      setShowUserLibrary(false)
      onSlideUpdated()
    } catch (err) {
      toast(err.message || 'Failed to apply visual.', 'error')
    } finally {
      setLoading(false)
    }
  }

  // 3. Upload User Visual
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setLoading(true)
    try {
      const asset = await api.uploadVisualAsset(file)
      // Apply uploaded asset directly to the slide
      const formattedImage = {
        url: asset.secure_url,
        thumb_url: asset.secure_url,
        title: asset.title,
        description: asset.description,
        source: 'User Upload',
        artist: 'User Asset',
        license: 'Proprietary Asset',
        dimensions: {
          width: asset.width,
          height: asset.height,
          aspect_ratio: asset.aspect_ratio,
        },
        is_company_logo: asset.is_company_logo,
        is_product_photo: asset.is_product_photo,
        alt: asset.title,
      }
      await api.selectSlideVisual(presentationId, slide.position, formattedImage)
      toast('Custom asset uploaded and applied to slide!', 'success')
      onSlideUpdated()
    } catch (err) {
      toast(err.message || 'Upload failed.', 'error')
    } finally {
      setLoading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // 4. Browse User Asset Library
  const handleOpenLibrary = async () => {
    setLoading(true)
    setShowUserLibrary(true)
    setShowCandidates(false)
    try {
      const assets = await api.listVisualAssets()
      setUserAssets(assets || [])
    } catch (err) {
      toast(err.message || 'Failed to load user assets.', 'error')
      setShowUserLibrary(false)
    } finally {
      setLoading(false)
    }
  }

  // 5. Remove Visual
  const handleRemoveVisual = async () => {
    setLoading(true)
    try {
      await api.removeSlideVisual(presentationId, slide.position)
      toast('Visual removed from slide.', 'success')
      onSlideUpdated()
    } catch (err) {
      toast(err.message || 'Failed to remove visual.', 'error')
    } finally {
      setLoading(false)
    }
  }

  // 6. Switch to Diagram
  const handleSwitchToDiagram = async () => {
    setLoading(true)
    try {
      await api.switchSlideToDiagram(presentationId, slide.position)
      toast('Slide transformed into a structured process diagram!', 'success')
      onSlideUpdated()
    } catch (err) {
      toast(err.message || 'Failed to switch to diagram.', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2 dark:border-slate-800">
        <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-slate-400">
          <ImageIcon size={13} />
          <span>Visual Asset Studio</span>
        </div>
        {currentImage && (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400">
            Active Visual
          </span>
        )}
      </div>

      {/* Current Visual Preview Card */}
      {currentImage ? (
        <div className="group relative overflow-hidden rounded-xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/60">
          <div className="aspect-video w-full overflow-hidden bg-slate-200 dark:bg-slate-800">
            <img
              src={currentImage.url}
              alt={currentImage.alt || 'Slide visual'}
              className="h-full w-full object-cover transition group-hover:scale-105"
            />
          </div>
          <div className="p-2.5">
            <div className="truncate text-xs font-semibold text-slate-800 dark:text-slate-200">
              {currentImage.title || currentImage.alt || 'Slide Photograph'}
            </div>
            <div className="mt-1 flex items-center justify-between text-[10px] text-slate-400">
              <span className="truncate">
                {currentImage.artist ? `By ${currentImage.artist}` : currentImage.source}
              </span>
              <span className="rounded bg-slate-200/80 px-1.5 py-0.5 font-mono text-[9px] dark:bg-slate-800">
                {currentImage.source || 'Curated'}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-200 p-4 text-center dark:border-slate-800">
          <ImageIcon size={22} className="mx-auto text-slate-400" />
          <p className="mt-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">
            No visual asset placed on this slide.
          </p>
          <p className="text-[11px] text-slate-400">
            Intelligently find photography or upload your brand logo.
          </p>
        </div>
      )}

      {/* Primary Actions Grid */}
      <div className="grid grid-cols-2 gap-2">
        {/* Find a Better Visual */}
        <button
          onClick={handleFindBetterVisual}
          disabled={loading}
          className="col-span-2 flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-3 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-brand-500 disabled:opacity-50"
        >
          {loading && showCandidates ? (
            <Loader2 size={13} className="animate-spin" />
          ) : (
            <Sparkles size={13} />
          )}
          Find a Better Visual
        </button>

        {/* Upload Visual */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          className="flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <Upload size={12} />
          Upload Visual
        </button>

        {/* Replace from Library */}
        <button
          onClick={handleOpenLibrary}
          disabled={loading}
          className="flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <Layers size={12} />
          My Assets
        </button>

        {/* Switch to Diagram */}
        <button
          onClick={handleSwitchToDiagram}
          disabled={loading}
          className="flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <GitCommit size={12} />
          To Diagram
        </button>

        {/* Remove Visual */}
        {currentImage && (
          <button
            onClick={handleRemoveVisual}
            disabled={loading}
            className="flex items-center justify-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-600 transition hover:bg-rose-100 disabled:opacity-50 dark:border-rose-950 dark:bg-rose-950/40 dark:text-rose-400"
          >
            <Trash2 size={12} />
            Remove
          </button>
        )}
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept="image/png,image/jpeg,image/webp,image/svg+xml"
        className="hidden"
      />

      {/* Candidate Picker Modal / Flyout */}
      {showCandidates && (
        <div className="rounded-xl border border-brand-200 bg-brand-50/40 p-3.5 dark:border-brand-900/60 dark:bg-brand-950/20">
          <div className="flex items-center justify-between pb-2">
            <div className="text-xs font-bold text-brand-950 dark:text-brand-200">
              AI Candidate Recommendations
            </div>
            <button
              onClick={() => setShowCandidates(false)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X size={14} />
            </button>
          </div>

          {brief && (
            <div className="mb-2.5 rounded-lg bg-white/80 p-2 text-[10px] text-slate-600 dark:bg-slate-900/80 dark:text-slate-400">
              <span className="font-semibold text-brand-600 dark:text-brand-400">
                Visual Intent:
              </span>{' '}
              {brief.main_message}
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-6 text-xs text-slate-500">
              <Loader2 className="mb-2 animate-spin text-brand-600" size={20} />
              Searching Wikimedia Commons & verified image sources...
            </div>
          ) : candidates.length === 0 ? (
            <p className="py-4 text-center text-xs text-slate-400">
              No matching candidate images found for this brief.
            </p>
          ) : (
            <div className="max-h-80 space-y-2.5 overflow-y-auto pr-1">
              {candidates.map((cand, idx) => (
                <div
                  key={idx}
                  className="flex gap-2.5 rounded-xl border border-slate-200/90 bg-white p-2 shadow-xs transition hover:border-brand-500 dark:border-slate-800 dark:bg-slate-900"
                >
                  <img
                    src={cand.thumb_url || cand.image_url}
                    alt={cand.title}
                    className="h-16 w-24 shrink-0 rounded-lg object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                    }}
                  />
                  <div className="flex min-w-0 flex-1 flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between gap-1">
                        <span className="truncate text-xs font-bold text-slate-800 dark:text-white">
                          {cand.title}
                        </span>
                        <span className="shrink-0 rounded bg-brand-100 px-1.5 py-0.5 text-[9px] font-extrabold text-brand-700 dark:bg-brand-950 dark:text-brand-300">
                          {Math.round(cand.score || 85)}% match
                        </span>
                      </div>
                      <p className="line-clamp-2 text-[10px] text-slate-500 dark:text-slate-400">
                        {cand.relevance_rationale || cand.description}
                      </p>
                    </div>

                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-[9px] text-slate-400">
                        {cand.source} • {cand.artist || 'CC'}
                      </span>
                      <button
                        onClick={() => handleSelectCandidate(cand)}
                        className="rounded-lg bg-slate-900 px-2 py-1 text-[10px] font-bold text-white hover:bg-brand-600 dark:bg-white dark:text-slate-900 dark:hover:bg-brand-400"
                      >
                        Apply
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* User Library Picker */}
      {showUserLibrary && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-800 dark:bg-slate-900/60">
          <div className="flex items-center justify-between pb-2">
            <div className="text-xs font-bold text-slate-800 dark:text-white">
              My Asset Library
            </div>
            <button
              onClick={() => setShowUserLibrary(false)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X size={14} />
            </button>
          </div>

          {userAssets.length === 0 ? (
            <div className="py-4 text-center text-xs text-slate-400">
              No assets in your library yet. Upload a company logo or product photo above.
            </div>
          ) : (
            <div className="max-h-60 space-y-2 overflow-y-auto">
              {userAssets.map((asset) => (
                <div
                  key={asset.id}
                  className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-800 dark:bg-slate-900"
                >
                  <img
                    src={asset.secure_url}
                    alt={asset.title}
                    className="h-10 w-14 rounded object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium text-slate-800 dark:text-slate-200">
                      {asset.title}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {asset.visual_category} • {Math.round(asset.size_bytes / 1024)} KB
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      handleSelectCandidate({
                        image_url: asset.secure_url,
                        thumb_url: asset.secure_url,
                        title: asset.title,
                        description: asset.description,
                        source: 'User Upload',
                        artist: 'User Asset',
                        license: 'Proprietary Asset',
                        width: asset.width,
                        height: asset.height,
                        aspect_ratio: asset.aspect_ratio,
                        score: 95,
                      })
                    }
                    className="rounded-md bg-brand-600 px-2 py-1 text-[10px] font-bold text-white hover:bg-brand-500"
                  >
                    Select
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import {
  X,
  Settings,
  Sliders,
  Palette,
  Cloud,
  User,
  Shield,
  Check,
  Moon,
  Sun,
  Monitor,
  ExternalLink,
  Cpu,
  Sparkles,
  Download,
  Trash2,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react'
import { api } from '../services/api'
import { useApp } from '../context/AppContext'
import { DESIGN_SYSTEMS, getDesignSystemById } from '../services/designSystems'

export default function SettingsModal({ onClose, onOpenLogin }) {
  const {
    theme,
    setTheme,
    user,
    logout,
    toast,
    startGoogle,
    disconnectGoogle,
    preferences,
    updatePreferences,
  } = useApp()

  const [activeTab, setActiveTab] = useState('ai')
  const [googleBusy, setGoogleBusy] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleExportData = async () => {
    setExporting(true)
    try {
      const res = await api.exportUserData()
      const dataStr = JSON.stringify(res, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `slidemind-data-export-${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast('Your data archive has been exported successfully.', 'success')
    } catch (err) {
      toast(err.message || 'Failed to export user data.', 'error')
    } finally {
      setExporting(false)
    }
  }

  const handleDeleteAccount = async () => {
    setDeleting(true)
    try {
      await api.deleteAccount()
      toast('Your account and all associated data have been permanently erased.', 'info')
      onClose()
      window.location.href = '/'
    } catch (err) {
      toast(err.message || 'Failed to delete account.', 'error')
      setDeleting(false)
    }
  }

  const handleGoogleToggle = async () => {
    setGoogleBusy(true)
    try {
      if (user?.google_connected) {
        await disconnectGoogle()
        toast('Google account disconnected.', 'info')
      } else {
        await startGoogle()
      }
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setGoogleBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md">
      <div className="flex h-[90vh] max-h-[640px] w-full max-w-2xl flex-col overflow-hidden liquid-glass-modal shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/[0.08] px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#F28C28]/15 border border-[#F28C28]/30 text-[#F28C28]">
              <Settings size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#F4E6D3]">Studio Settings</h2>
              <p className="text-xs text-[#888A90]">Configure presentation design preferences and connected accounts</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#888A90] hover:text-[#F4E6D3] hover:bg-white/[0.08] cursor-pointer transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-white/[0.08] bg-[#101114]/50 px-6">
          {[
            { id: 'ai', label: 'AI & Design Defaults', icon: Sparkles },
            { id: 'integrations', label: 'Google & Export', icon: Cloud },
            { id: 'appearance', label: 'Appearance', icon: Palette },
            { id: 'account', label: 'Account Profile', icon: User },
          ].map((tab) => {
            const Icon = tab.icon
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 border-b-2 px-3 py-3 text-xs font-semibold transition-colors cursor-pointer ${
                  active
                    ? 'border-[#F28C28] text-[#F28C28]'
                    : 'border-transparent text-[#888A90] hover:text-[#F4E6D3]'
                }`}
              >
                <Icon size={14} />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>

        {/* Tab Body */}
        <div className="flex-1 overflow-y-auto p-6 text-sm">
          {/* TAB 1: AI & Design Defaults */}
          {activeTab === 'ai' && (
            <div className="space-y-6">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#888A90]">
                  Default Design System
                </label>
                <p className="mt-0.5 text-xs text-[#888A90]">Preferred visual system for newly generated decks</p>
                <select
                  value={getDesignSystemById(preferences?.defaultDesignSystem || 'linear_dark')?.id || 'linear_dark'}
                  onChange={(e) => updatePreferences({ defaultDesignSystem: e.target.value })}
                  className="mt-2 w-full rounded-xl border border-white/[0.12] bg-[#1E2026] p-2.5 text-xs text-[#F4E6D3] outline-none focus:border-[#F28C28]"
                >
                  {DESIGN_SYSTEMS.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.category})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#888A90]">
                    Default Slide Count
                  </label>
                  <p className="mt-0.5 text-xs text-[#888A90]">Target deck length</p>
                  <select
                    value={preferences?.defaultSlideCount || 10}
                    onChange={(e) => updatePreferences({ defaultSlideCount: Number(e.target.value) })}
                    className="mt-2 w-full rounded-xl border border-white/[0.12] bg-[#1E2026] p-2.5 text-xs text-[#F4E6D3] outline-none focus:border-[#F28C28]"
                  >
                    {[3, 5, 7, 10, 12, 15, 20].map((n) => (
                      <option key={n} value={n}>
                        {n} Slides
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#888A90]">
                    Content Density
                  </label>
                  <p className="mt-0.5 text-xs text-[#888A90]">Text-to-whitespace ratio</p>
                  <select
                    value={preferences?.density || 'balanced'}
                    onChange={(e) => updatePreferences({ density: e.target.value })}
                    className="mt-2 w-full rounded-xl border border-white/[0.12] bg-[#1E2026] p-2.5 text-xs text-[#F4E6D3] outline-none focus:border-[#F28C28]"
                  >
                    <option value="minimal">Minimalist (1 Key Point / Slide)</option>
                    <option value="balanced">Balanced (Executive Standard)</option>
                    <option value="detailed">Comprehensive (Deep Dive)</option>
                  </select>
                </div>
              </div>

              {/* Automated Audit Toggle */}
              <div className="flex items-center justify-between rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
                <div>
                  <div className="font-semibold text-[#F4E6D3]">
                    Automated Design Quality Auditor
                  </div>
                  <div className="mt-0.5 text-xs text-[#888A90]">
                    Runs real-time pre-flight audits for text overflow, layout monotony, and color contrast.
                  </div>
                </div>
                <button
                  onClick={() => updatePreferences({ autoAudit: !preferences?.autoAudit })}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    preferences?.autoAudit !== false ? 'bg-[#F28C28]' : 'bg-white/20'
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      preferences?.autoAudit !== false ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* Active Model Info */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#F4E6D3]">
                  <Cpu size={14} className="text-[#F28C28]" />
                  <span>Intelligence Engine: Gemini 3.5 Flash Lite</span>
                </div>
                <p className="mt-1 text-xs text-[#888A90]">
                  Structured multi-turn tool calling, RAG embeddings with pgvector / SQLite, and automated visual enrichment.
                </p>
              </div>
            </div>
          )}

          {/* TAB 2: Google & Export */}
          {activeTab === 'integrations' && (
            <div className="space-y-6">
              {/* Google Slides Card */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-[#F4E6D3]">Google Slides Integration</h3>
                    <p className="mt-1 text-xs text-[#888A90]">
                      Sync presentations to Google Slides in real-time with your Google Drive account.
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                      user?.google_connected
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : 'bg-white/[0.06] text-[#888A90] border border-white/[0.08]'
                    }`}
                  >
                    {user?.google_connected ? 'Connected' : 'Not Connected'}
                  </span>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-white/[0.08] pt-3">
                  <span className="text-xs text-[#888A90]">
                    {user?.google_connected ? 'Scopes: Drive File, Presentations Edit' : 'Connect for 1-click cloud sync'}
                  </span>
                  <button
                    disabled={googleBusy}
                    onClick={handleGoogleToggle}
                    className={`rounded-lg px-4 py-1.5 text-xs font-semibold shadow-xs transition cursor-pointer ${
                      user?.google_connected
                        ? 'border border-red-400/30 text-red-400 hover:bg-red-500/10'
                        : 'liquid-glass-btn-primary text-[#101114]'
                    }`}
                  >
                    {googleBusy ? 'Processing...' : user?.google_connected ? 'Disconnect Google' : 'Connect Google Slides'}
                  </button>
                </div>
              </div>

              {/* Direct Export Preferences */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-5">
                <div className="flex items-center gap-2">
                  <Download size={16} className="text-[#F28C28]" />
                  <h3 className="font-bold text-[#F4E6D3]">Offline Native Export</h3>
                </div>
                <p className="mt-1 text-xs text-[#888A90]">
                  SlideMind AI generates standalone widescreen PPTX and vector PDF presentations directly—no Google Cloud required.
                </p>

                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-[#C5C0B8]">
                      Default Export Format
                    </label>
                    <select
                      value={preferences?.defaultFormat || 'pptx'}
                      onChange={(e) => updatePreferences({ defaultFormat: e.target.value })}
                      className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-[#1E2026] p-2 text-xs text-[#F4E6D3] outline-none focus:border-[#F28C28]"
                    >
                      <option value="pptx">PowerPoint (.pptx) - Fully Editable</option>
                      <option value="pdf">Document (.pdf) - 16:9 Vector Render</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Appearance */}
          {activeTab === 'appearance' && (
            <div className="space-y-6">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#888A90]">
                  Theme Mode
                </label>
                <div className="mt-3 grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setTheme('dark')}
                    className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition cursor-pointer ${
                      theme === 'dark'
                        ? 'border-[#F28C28] bg-[#F28C28]/10 text-[#F28C28]'
                        : 'border-white/[0.08] bg-white/[0.02] text-[#C5C0B8] hover:border-white/[0.16]'
                    }`}
                  >
                    <Moon size={24} />
                    <span className="text-xs font-bold text-[#F4E6D3]">Dark Obsidian</span>
                    <span className="text-[11px] text-[#888A90]">Modern low-glare canvas</span>
                  </button>

                  <button
                    onClick={() => setTheme('light')}
                    className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition cursor-pointer ${
                      theme === 'light'
                        ? 'border-[#F28C28] bg-[#F28C28]/10 text-[#F28C28]'
                        : 'border-white/[0.08] bg-white/[0.02] text-[#C5C0B8] hover:border-white/[0.16]'
                    }`}
                  >
                    <Sun size={24} />
                    <span className="text-xs font-bold text-[#F4E6D3]">Clean Light</span>
                    <span className="text-[11px] text-[#888A90]">Crisp high-contrast daylight</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Account */}
          {activeTab === 'account' && (
            <div className="space-y-6">
              <div className="flex items-center gap-4 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-tr from-[#F28C28] to-[#DFA36D] text-lg font-bold text-[#101114] shadow-md">
                  {(user?.name || user?.email || '?')[0].toUpperCase()}
                </div>
                <div>
                  <div className="font-bold text-[#F4E6D3]">
                    {user?.name || 'SlideMind Creator'}
                  </div>
                  <div className="text-xs text-[#888A90]">{user?.email}</div>
                  <span className="mt-1 inline-block rounded-md bg-[#F28C28]/15 border border-[#F28C28]/30 px-2 py-0.5 text-[10px] font-semibold text-[#F28C28]">
                    {user?.email?.startsWith('guest_') ? 'Guest Explorer' : 'Studio Workspace'}
                  </span>
                </div>
              </div>

              {user?.email?.startsWith('guest_') && onOpenLogin && (
                <div className="rounded-xl border border-[#F28C28]/35 bg-[#F28C28]/10 p-3.5 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-[#F4E6D3]">Temporary Guest Session</div>
                    <div className="text-[11px] text-[#C5C0B8]">Sign in with your email to keep your presentations permanently.</div>
                  </div>
                  <button
                    onClick={onOpenLogin}
                    className="liquid-glass-btn-primary px-3 py-1.5 rounded-lg text-xs font-semibold text-[#101114] cursor-pointer"
                  >
                    Sign In
                  </button>
                </div>
              )}

              {/* GDPR Compliance & Data Rights */}
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={16} className="text-[#F28C28]" />
                    <span className="text-xs font-bold text-[#F4E6D3]">Data Privacy & GDPR Rights</span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px]">
                    <a href="/privacy" target="_blank" rel="noreferrer" className="text-[#F28C28] hover:underline">
                      Privacy
                    </a>
                    <span className="text-white/20">·</span>
                    <a href="/terms" target="_blank" rel="noreferrer" className="text-[#F28C28] hover:underline">
                      Terms
                    </a>
                  </div>
                </div>
                <p className="text-[11px] text-[#888A90]">
                  You have full ownership of your data. You may download all account records or permanently erase your account at any time.
                </p>

                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <button
                    onClick={handleExportData}
                    disabled={exporting}
                    className="flex items-center gap-1.5 rounded-lg border border-white/[0.12] bg-white/[0.05] hover:bg-white/[0.1] px-3 py-1.5 text-xs text-[#F4E6D3] transition disabled:opacity-50 cursor-pointer"
                  >
                    <Download size={13} className="text-[#F28C28]" />
                    <span>{exporting ? 'Exporting JSON...' : 'Download My Data (JSON)'}</span>
                  </button>

                  {!confirmDelete ? (
                    <button
                      onClick={() => setConfirmDelete(true)}
                      className="flex items-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/10 hover:bg-red-500/20 px-3 py-1.5 text-xs text-red-400 transition cursor-pointer"
                    >
                      <Trash2 size={13} />
                      <span>Delete Account</span>
                    </button>
                  ) : (
                    <div className="flex items-center gap-2 p-1.5 rounded-lg bg-red-500/15 border border-red-500/30">
                      <AlertTriangle size={13} className="text-red-400" />
                      <span className="text-[11px] text-red-200">Confirm permanent deletion?</span>
                      <button
                        onClick={handleDeleteAccount}
                        disabled={deleting}
                        className="rounded px-2 py-0.5 text-[11px] font-bold bg-red-600 text-white hover:bg-red-700 cursor-pointer"
                      >
                        {deleting ? 'Erasing...' : 'Yes, Erase Everything'}
                      </button>
                      <button
                        onClick={() => setConfirmDelete(false)}
                        className="text-[11px] text-[#888A90] hover:text-[#F4E6D3] cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-between border-t border-white/[0.08] pt-4">
                <button
                  onClick={() => {
                    localStorage.removeItem('sm_preferences')
                    toast('Preferences reset to default.', 'info')
                  }}
                  className="text-xs text-[#888A90] hover:text-[#F4E6D3] cursor-pointer"
                >
                  Reset preferences to factory defaults
                </button>
                <button
                  onClick={logout}
                  className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-2 text-xs font-semibold text-red-400 transition hover:bg-red-500/20 cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-white/[0.08] bg-[#101114]/50 px-6 py-3">
          <span className="text-[11px] text-[#888A90]">SlideMind Studio · v2.5</span>
          <button
            onClick={onClose}
            className="liquid-glass-btn-primary rounded-full px-5 py-2 text-xs font-semibold text-[#101114] cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Menu, X, Sparkles, Layers, FileText, Settings, FolderOpen, ArrowRight } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function FloatingNavigation({
  onNavigate,
  currentView = 'home',
  onOpenDocuments,
  onOpenSettings,
  onOpenLogin,
}) {
  const { user, isPresenting } = useApp()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [hoveredTab, setHoveredTab] = useState(null)

  if (isPresenting) return null

  const handleNav = (view) => {
    setMobileMenuOpen(false)
    onNavigate?.(view)
  }

  const navItems = [
    {
      id: 'chat',
      label: 'Studio',
      icon: Sparkles,
      active: currentView === 'chat',
      onClick: () => handleNav('chat'),
    },
    {
      id: 'templates',
      label: 'Explore',
      icon: Layers,
      active: currentView === 'templates',
      onClick: () => handleNav('templates'),
    },
    {
      id: 'presentations',
      label: 'My Work',
      icon: FileText,
      active: currentView === 'presentations',
      onClick: () => handleNav('presentations'),
    },
    {
      id: 'resources',
      label: 'Resources',
      icon: FolderOpen,
      active: false,
      onClick: () => {
        if (onOpenDocuments) onOpenDocuments()
        else handleNav('home')
      },
    },
  ]

  return (
    <header className="fixed top-4 sm:top-6 left-1/2 -translate-x-1/2 w-[94%] max-w-6xl z-50 transition-all duration-300">
      {/* Obsidian Orange Liquid Glass Capsule */}
      <div className="liquid-glass-nav px-4 sm:px-6 py-2 sm:py-2.5 flex justify-between items-center w-full">
        {/* Brand Logotype */}
        <button
          onClick={() => handleNav('home')}
          className="flex items-center gap-2.5 group text-left cursor-pointer"
        >
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full border border-white/20 bg-white/[0.06] flex items-center justify-center transition-all duration-300 group-hover:border-[#F28C28]/60 group-hover:bg-[#F28C28]/12 group-hover:scale-105 shadow-[inset_0_1px_0_rgba(255,255,255,0.25)]">
            <span className="material-symbols-outlined text-[#F4E6D3] text-sm sm:text-base group-hover:text-[#F28C28] transition-colors" data-icon="deployed_code">
              deployed_code
            </span>
          </div>
          <span className="text-sm sm:text-base text-[#F4E6D3] tracking-tight font-semibold">
            SlideMind<span className="text-[#F28C28] font-normal">.ai</span>
          </span>
        </button>

        {/* Desktop Middle Navigation Cluster with Luxury Spring Sliding Capsule */}
        <nav
          onMouseLeave={() => setHoveredTab(null)}
          className="hidden md:flex items-center gap-1 bg-white/[0.03] border border-white/[0.09] rounded-full p-1 shadow-[inset_0_1px_2px_rgba(0,0,0,0.35),0_4px_16px_rgba(0,0,0,0.2)] relative"
        >
          {navItems.map((item) => {
            const Icon = item.icon
            const isHovered = hoveredTab === item.id
            const isActive = item.active

            return (
              <button
                key={item.id}
                onClick={item.onClick}
                onMouseEnter={() => setHoveredTab(item.id)}
                className={`group relative px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer flex items-center gap-1.5 select-none z-10 ${
                  isActive
                    ? 'text-[#F4E6D3] font-semibold'
                    : isHovered
                    ? 'text-white'
                    : 'text-[#C5C0B8] hover:text-white'
                }`}
              >
                {/* Active Animated Background Pill */}
                {isActive && (
                  <motion.div
                    layoutId="nav-active-capsule"
                    className="absolute inset-0 rounded-full bg-[#F28C28]/18 border border-[#F28C28]/45 shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_0_16px_rgba(242,140,40,0.28)] z-[-1]"
                    transition={{ type: 'spring', stiffness: 450, damping: 32 }}
                  />
                )}

                {/* Hover Animated Glow Pill */}
                {isHovered && !isActive && (
                  <motion.div
                    layoutId="nav-hover-capsule"
                    className="absolute inset-0 rounded-full bg-white/[0.08] border border-white/[0.18] shadow-[inset_0_1px_0_rgba(255,255,255,0.25),0_4px_16px_rgba(0,0,0,0.35),0_0_12px_rgba(242,140,40,0.12)] backdrop-blur-md z-[-1]"
                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                  />
                )}

                {/* Micro Icon with Dynamic Hover Physics */}
                <Icon
                  size={13}
                  className={`transition-all duration-200 ${
                    isActive
                      ? 'text-[#F28C28] scale-105'
                      : isHovered
                      ? 'text-[#F28C28] scale-115 rotate-3 drop-shadow-[0_0_8px_rgba(242,140,40,0.6)]'
                      : 'text-[#888A90] group-hover:text-[#DFA36D]'
                  }`}
                />

                <span className="relative tracking-tight font-medium">
                  {item.label}
                </span>

                {/* Active Indicator Dot */}
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#F28C28] shadow-[0_0_8px_#F28C28] animate-pulse" />
                )}
              </button>
            )
          })}
        </nav>

        {/* Trailing Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {user ? (
            <>
              {/* Google Slides Live Status Badge (Desktop) */}
              <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.1] text-[#C5C0B8] text-xs font-medium shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)] animate-pulse" />
                <span>{user?.google_connected ? 'Google Slides Synced' : 'Google Slides Connected'}</span>
              </div>

              {/* Guest Upgrade / Sign In CTA */}
              {user?.email?.startsWith('guest_') && (
                <button
                  onClick={() => onOpenLogin?.()}
                  className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold text-[#101114] bg-[#F28C28] hover:bg-[#F28C28]/90 transition-all cursor-pointer shadow-xs"
                >
                  Sign In
                </button>
              )}

              <button
                onClick={onOpenSettings}
                aria-label="Settings"
                className="w-8 h-8 sm:w-8.5 sm:h-8.5 rounded-full flex items-center justify-center border border-white/[0.12] bg-white/[0.04] hover:bg-white/[0.1] hover:border-white/25 transition-all duration-200 text-[#C5C0B8] hover:text-[#F4E6D3] cursor-pointer shadow-[inset_0_1px_0_rgba(255,255,255,0.15)]"
              >
                <span className="material-symbols-outlined text-base sm:text-lg" data-icon="tune">
                  tune
                </span>
              </button>

              {/* User Avatar */}
              <div
                onClick={onOpenSettings}
                className="relative cursor-pointer"
                title={user?.email || 'Profile'}
              >
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full overflow-hidden border border-white/25 ring-1 ring-[#F28C28]/25 bg-white/[0.08] flex items-center justify-center text-xs font-medium text-[#F4E6D3] shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]">
                  {(user?.name || user?.email || 'U')[0].toUpperCase()}
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-1.5 sm:gap-2">
              <button
                onClick={() => onOpenLogin?.()}
                className="px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-full text-xs sm:text-sm font-medium text-[#C5C0B8] hover:text-[#F4E6D3] hover:bg-white/[0.08] transition-all cursor-pointer"
              >
                Sign In
              </button>
              <button
                onClick={() => onOpenLogin?.()}
                className="liquid-glass-btn-primary px-3 sm:px-4 py-1 sm:py-1.5 rounded-full text-xs sm:text-sm font-semibold cursor-pointer"
              >
                Get Started
              </button>
            </div>
          )}

          {/* Mobile Hamburger Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
            className="md:hidden w-8 h-8 rounded-full flex items-center justify-center border border-white/[0.12] bg-white/[0.05] text-[#F4E6D3] hover:bg-white/10 transition-colors cursor-pointer"
          >
            {mobileMenuOpen ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-2 rounded-2xl liquid-glass-popover p-3 shadow-2xl animate-in fade-in slide-in-from-top-3 duration-200">
          <nav className="flex flex-col gap-1.5">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = item.active

              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setMobileMenuOpen(false)
                    item.onClick()
                  }}
                  className={`group flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 cursor-pointer ${
                    isActive
                      ? 'bg-[#F28C28]/16 border border-[#F28C28]/40 text-[#F4E6D3] font-semibold shadow-[0_0_12px_rgba(242,140,40,0.2)]'
                      : 'text-[#C5C0B8] border border-transparent hover:border-white/[0.12] hover:bg-white/[0.06] hover:text-[#F4E6D3] hover:translate-x-1'
                  }`}
                >
                  <span className="flex items-center gap-2.5">
                    <span
                      className={`w-7 h-7 rounded-lg border flex items-center justify-center transition-all ${
                        isActive
                          ? 'bg-[#F28C28]/20 border-[#F28C28]/50 text-[#F28C28]'
                          : 'bg-white/[0.04] border-white/[0.08] text-[#888A90] group-hover:bg-[#F28C28]/15 group-hover:border-[#F28C28]/40 group-hover:text-[#F28C28]'
                      }`}
                    >
                      <Icon size={14} />
                    </span>
                    <span className="tracking-tight">{item.label}</span>
                  </span>
                  <ArrowRight
                    size={14}
                    className="opacity-40 group-hover:opacity-100 group-hover:text-[#F28C28] group-hover:translate-x-0.5 transition-all"
                  />
                </button>
              )
            })}

            <button
              onClick={() => {
                setMobileMenuOpen(false)
                onOpenSettings?.()
              }}
              className="group flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium text-[#C5C0B8] border border-transparent hover:border-white/[0.12] hover:bg-white/[0.06] hover:text-[#F4E6D3] hover:translate-x-1 transition-all cursor-pointer mt-1 pt-2 border-t border-white/[0.08]"
            >
              <span className="flex items-center gap-2.5">
                <span className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-[#888A90] group-hover:bg-[#F28C28]/15 group-hover:border-[#F28C28]/40 group-hover:text-[#F28C28] transition-all">
                  <Settings size={14} />
                </span>
                <span>Preferences & Google Auth</span>
              </span>
              <ArrowRight
                size={14}
                className="opacity-40 group-hover:opacity-100 group-hover:text-[#F28C28] group-hover:translate-x-0.5 transition-all"
              />
            </button>
          </nav>
        </div>
      )}
    </header>
  )
}

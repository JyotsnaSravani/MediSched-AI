import React, { ReactNode, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import Icon from './Icon'
import { useAuth } from '../contexts/AuthContext'
import { useConfirm } from './ConfirmDialog'
import CommandPalette from './CommandPalette'
import Popover from './Popover'
import NotificationsPopover from './NotificationsPopover'
import SettingsMenu from './SettingsMenu'

interface SimpleLayoutProps {
  children: ReactNode
  title: string
}

const SimpleLayout: React.FC<SimpleLayoutProps> = ({ children, title }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const confirm = useConfirm()
  const { user, isAdmin, isReadOnly, isDoctor, isStaff, signOut } = useAuth()
  const [params] = useSearchParams()

  const [mobileOpen, setMobileOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [notifOpen, setNotifOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const [searchValue, setSearchValue] = useState(params.get('q') || '')
  const searchRef = useRef<HTMLInputElement>(null)
  const notifRef = useRef<HTMLButtonElement>(null)
  const settingsRef = useRef<HTMLButtonElement>(null)

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false)
    setNotifOpen(false)
    setSettingsOpen(false)
  }, [location.pathname])

  // Reflect URL ?q= into the topbar input on live-search pages
  useEffect(() => {
    setSearchValue(params.get('q') || '')
  }, [params, location.pathname])

  // Cmd/Ctrl+K opens the global command palette
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteQuery('')
        setPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const liveSearchPaths = ['/patients', '/doctors', '/call-logs']
  const isLiveSearch = liveSearchPaths.includes(location.pathname)

  const handleSearchChange = (v: string) => {
    setSearchValue(v)
    if (isLiveSearch) {
      const next = new URLSearchParams(params)
      if (v) next.set('q', v)
      else next.delete('q')
      navigate(
        { pathname: location.pathname, search: next.toString() ? `?${next}` : '' },
        { replace: true }
      )
    }
  }

  const handleLogout = async () => {
    const ok = await confirm({
      title: 'Sign out of MediSched AI?',
      message: 'You will need to sign in again to access the dashboard.',
      confirmLabel: 'Sign out',
      variant: 'danger',
    })
    if (ok) signOut()
  }

  // Build nav with role-aware visibility
  const nav = [
    {
      label: 'Overview',
      items: [
        { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' as const, path: '/dashboard', visible: !isDoctor && !isStaff },
        { id: 'analytics', label: 'Analytics', icon: 'analytics' as const, path: '/analytics', visible: !isDoctor && !isStaff },
      ],
    },
    {
      label: 'Scheduling',
      items: [
        { id: 'calendar', label: 'Calendar', icon: 'calendar' as const, path: '/calendar', visible: true },
        { id: 'slots', label: 'Availability', icon: 'clock' as const, path: '/slots', visible: !isReadOnly },
      ],
    },
    {
      label: 'People',
      items: [
        { id: 'patients', label: 'Patients', icon: 'patients' as const, path: '/patients', visible: true },
        { id: 'doctors', label: 'Doctors', icon: 'stethoscope' as const, path: '/doctors', visible: true },
      ],
    },
    {
      label: 'Engagement',
      items: [
        { id: 'call-logs', label: 'Call Logs', icon: 'phone' as const, path: '/call-logs', visible: !isReadOnly && !isDoctor },
        { id: 'reminders', label: 'Reminders', icon: 'bell' as const, path: '/reminders', visible: !isReadOnly && !isDoctor },
      ],
    },
    {
      label: 'Admin',
      items: [
        { id: 'users', label: 'Users', icon: 'users' as const, path: '/users', visible: isAdmin },
      ],
    },
  ]
    .map((s) => ({ ...s, items: s.items.filter((i) => i.visible) }))
    .filter((s) => s.items.length > 0)

  const email: string = user?.email || 'user@medisched.com'
  const role: string = user?.role_display || user?.role || 'USER'
  const initials = email
    .split('@')[0]
    .split(/[._-]/)
    .map((p: string) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <aside
        id="primary-nav"
        className={`sidebar ${mobileOpen ? 'open' : ''}`}
        aria-label="Primary navigation"
      >
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark">
            <Icon name="pulse" size={20} />
          </div>
          <div className="sidebar-brand-text">
            <h1>MediSched AI</h1>
            <p>Healthcare OS</p>
          </div>
        </div>

        <nav style={{ flex: 1, overflowY: 'auto' }} aria-label="Main">
          {nav.map((section) => (
            <div key={section.label}>
              <div className="sidebar-section-label" id={`nav-${section.label}`}>
                {section.label}
              </div>
              <div
                className="sidebar-nav"
                role="group"
                aria-labelledby={`nav-${section.label}`}
              >
                {section.items.map((item) => {
                  const isActive = location.pathname === item.path
                  return (
                    <button
                      key={item.id}
                      onClick={() => navigate(item.path)}
                      className={`sidebar-link ${isActive ? 'active' : ''}`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <Icon name={item.icon} />
                      <span>{item.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <button
              type="button"
              onClick={() => navigate('/profile')}
              aria-label="Open my profile"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: 'transparent',
                border: 0,
                color: 'inherit',
                cursor: 'pointer',
                flex: 1,
                minWidth: 0,
                padding: 0,
                font: 'inherit',
                textAlign: 'left',
              }}
            >
              <div className="sidebar-user-avatar" aria-hidden="true">
                {initials}
              </div>
              <div className="sidebar-user-info">
                <strong>{email}</strong>
                <span>{role}</span>
              </div>
            </button>
            <button
              className="sidebar-logout"
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <Icon name="logout" size={16} />
            </button>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <div
          className="sidebar-backdrop open"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <main className="app-main" id="main-content">
        <header className="app-topbar">
          <div style={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
            <button
              className="mobile-menu-btn"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
              aria-controls="primary-nav"
            >
              <Icon name="menu" />
            </button>
            <div className="app-topbar-title">{title}</div>
          </div>
          <div className="app-topbar-actions">
            <button
              type="button"
              className="topbar-search-trigger"
              onClick={() => {
                setPaletteQuery(searchValue)
                setPaletteOpen(true)
              }}
              aria-label="Open search"
            >
              <Icon name="search" size={14} />
              <span>{isLiveSearch ? 'Search this list…' : 'Search anything…'}</span>
              <span className="topbar-search-kbd-inline" aria-hidden="true">
                <kbd className="kbd">{isMac ? '⌘' : 'Ctrl'}</kbd>
                <kbd className="kbd" style={{ marginLeft: 2 }}>
                  K
                </kbd>
              </span>
            </button>

            {isLiveSearch && (
              <input
                ref={searchRef}
                type="search"
                placeholder="Filter…"
                className="topbar-search topbar-search-inline"
                aria-label="Filter list"
                value={searchValue}
                onChange={(e) => handleSearchChange(e.target.value)}
              />
            )}

            <div style={{ position: 'relative' }}>
              <button
                ref={notifRef}
                className="topbar-iconbtn"
                aria-label="Notifications"
                aria-expanded={notifOpen}
                onClick={() => {
                  setSettingsOpen(false)
                  setNotifOpen((v) => !v)
                }}
              >
                <Icon name="bell" />
                <span className="dot" />
              </button>
              <Popover
                open={notifOpen}
                onClose={() => setNotifOpen(false)}
                anchorRef={notifRef}
                ariaLabel="Notifications"
                width={360}
              >
                <NotificationsPopover open={notifOpen} onClose={() => setNotifOpen(false)} />
              </Popover>
            </div>

            <div style={{ position: 'relative' }}>
              <button
                ref={settingsRef}
                className="topbar-iconbtn"
                aria-label="Settings and account"
                aria-expanded={settingsOpen}
                onClick={() => {
                  setNotifOpen(false)
                  setSettingsOpen((v) => !v)
                }}
              >
                <Icon name="settings" />
              </button>
              <Popover
                open={settingsOpen}
                onClose={() => setSettingsOpen(false)}
                anchorRef={settingsRef}
                ariaLabel="Settings menu"
                width={260}
              >
                <SettingsMenu onClose={() => setSettingsOpen(false)} />
              </Popover>
            </div>
          </div>
        </header>

        <div className="app-page">{children}</div>
      </main>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        initialQuery={paletteQuery}
      />
    </div>
  )
}

export default SimpleLayout

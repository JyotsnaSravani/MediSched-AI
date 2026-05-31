import React from 'react'
import { Link } from 'react-router-dom'
import Icon from './Icon'
import { useAuth } from '../contexts/AuthContext'
import { useConfirm } from './ConfirmDialog'

interface Props {
  onClose: () => void
}

const SettingsMenu: React.FC<Props> = ({ onClose }) => {
  const { user, isAdmin, signOut } = useAuth()
  const confirm = useConfirm()

  const handleSignOut = async () => {
    onClose()
    const ok = await confirm({
      title: 'Sign out of MediSched AI?',
      message: 'You will need to sign in again to access the dashboard.',
      confirmLabel: 'Sign out',
      variant: 'danger',
    })
    if (ok) signOut()
  }

  const initials = (user?.email || 'U')
    .split('@')[0]
    .split(/[._-]/)
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="menu">
      <div className="menu-header">
        <div className="sidebar-user-avatar" style={{ width: 36, height: 36, fontSize: 13 }}>
          {initials}
        </div>
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {user?.full_name || user?.email || 'User'}
          </div>
          <div className="small-muted">{user?.role_display || user?.role}</div>
        </div>
      </div>

      <div className="menu-divider" />

      <Link to="/profile" className="menu-item" onClick={onClose}>
        <Icon name="user" size={16} />
        <span>My profile</span>
      </Link>

      {isAdmin && (
        <Link to="/users" className="menu-item" onClick={onClose}>
          <Icon name="users" size={16} />
          <span>User management</span>
        </Link>
      )}

      <a
        href="http://localhost:8000/api/schema/swagger-ui/"
        target="_blank"
        rel="noreferrer"
        className="menu-item"
        onClick={onClose}
      >
        <Icon name="clipboard" size={16} />
        <span>API docs</span>
      </a>

      <div className="menu-divider" />

      <button className="menu-item menu-item-danger" onClick={handleSignOut}>
        <Icon name="logout" size={16} />
        <span>Sign out</span>
      </button>
    </div>
  )
}

export default SettingsMenu

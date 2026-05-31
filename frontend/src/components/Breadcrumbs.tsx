import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import Icon from './Icon'

const labelMap: Record<string, string> = {
  dashboard: 'Dashboard',
  patients: 'Patients',
  doctors: 'Doctors',
  calendar: 'Calendar',
  slots: 'Availability',
  'call-logs': 'Call Logs',
  reminders: 'Reminders',
  analytics: 'Analytics',
  users: 'Users',
  transcriptions: 'Transcriptions',
}

const prettify = (seg: string) =>
  labelMap[seg] ||
  seg.replace(/-/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase())

const Breadcrumbs: React.FC<{ trailing?: string }> = ({ trailing }) => {
  const { pathname } = useLocation()
  const parts = pathname.split('/').filter(Boolean)

  if (parts.length === 0) return null

  return (
    <nav aria-label="Breadcrumb" className="breadcrumbs">
      <ol>
        <li>
          <Link to="/dashboard">
            <Icon name="dashboard" size={12} />
            <span>Home</span>
          </Link>
        </li>
        {parts.map((seg, i) => {
          const to = '/' + parts.slice(0, i + 1).join('/')
          const isLast = i === parts.length - 1 && !trailing
          return (
            <li key={to} aria-current={isLast ? 'page' : undefined}>
              <Icon name="chevron-right" size={12} className="breadcrumb-sep" />
              {isLast ? (
                <span>{prettify(seg)}</span>
              ) : (
                <Link to={to}>{prettify(seg)}</Link>
              )}
            </li>
          )
        })}
        {trailing && (
          <li aria-current="page">
            <Icon name="chevron-right" size={12} className="breadcrumb-sep" />
            <span>{trailing}</span>
          </li>
        )}
      </ol>
    </nav>
  )
}

export default Breadcrumbs

import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import Icon from '../components/Icon'

const StandaloneLoginPage: React.FC = () => {
  const [email, setEmail] = useState('test@test.com')
  const [password, setPassword] = useState('Test@123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) navigate('/dashboard')
  }, [navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await axios.post('http://127.0.0.1:8000/api/v1/auth/login/', { email, password })
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      localStorage.setItem('user', JSON.stringify(data.user))
      window.location.href = '/dashboard'
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-shell">
      {/* Left panel — brand */}
      <aside className="login-aside">
        <div className="login-aside-brand">
          <div className="login-aside-brand-mark">
            <Icon name="pulse" size={22} />
          </div>
          <div>
            <h1>MediSched AI</h1>
            <p>Healthcare OS</p>
          </div>
        </div>

        <div className="login-hero">
          <h2>Scheduling that thinks&nbsp;for&nbsp;itself.</h2>
          <p>
            The intelligent operations platform for diagnostic centers — unify patient
            records, doctor availability, AI calling, and analytics in a single
            workspace.
          </p>

          <div className="login-features">
            <div className="login-feature">
              <span className="login-feature-dot"><Icon name="check" size={12} /></span>
              <span className="login-feature-text">
                <strong>Real-time calendar</strong>
                Conflict-free booking with live WebSocket updates
              </span>
            </div>
            <div className="login-feature">
              <span className="login-feature-dot"><Icon name="check" size={12} /></span>
              <span className="login-feature-text">
                <strong>AI outbound calling</strong>
                Three-attempt escalation with human fallback
              </span>
            </div>
            <div className="login-feature">
              <span className="login-feature-dot"><Icon name="check" size={12} /></span>
              <span className="login-feature-text">
                <strong>Call transcription</strong>
                Automatic Whisper transcripts tagged to appointments
              </span>
            </div>
          </div>
        </div>

        <div className="login-aside-foot">© 2026 SmartX Technologies · MediSched AI</div>
      </aside>

      {/* Right panel — form */}
      <section className="login-main">
        <div className="login-card">
          <h2 className="login-card-title">Welcome back</h2>
          <p className="login-card-sub">Sign in to continue to your workspace.</p>

          {error && (
            <div className="alert alert-error">
              <Icon name="x" size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email address</label>
              <input
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@clinic.com"
                autoComplete="email"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
            </div>

            <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
              {loading ? (
                <>
                  <span className="spinner spinner-on-dark" />
                  <span>Signing in…</span>
                </>
              ) : (
                <>
                  <span>Sign in</span>
                  <Icon name="chevron-right" size={16} />
                </>
              )}
            </button>
          </form>

          <div className="login-demo">
            <span className="login-demo-icon"><Icon name="sparkles" size={16} /></span>
            <div>
              <strong>Demo account:</strong>{' '}
              <code>test@test.com</code> · <code>Test@123</code>
            </div>
          </div>

          <p className="login-foot">
            Secured by JWT · Protected by role-based access control
          </p>
        </div>
      </section>
    </div>
  )
}

export default StandaloneLoginPage

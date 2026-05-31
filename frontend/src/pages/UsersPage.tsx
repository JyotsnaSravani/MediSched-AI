/**
 * Users Management Page (Admin only)
 * Create, edit, activate/deactivate users with role-based access.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { userService, UserCreateData } from '../services/userService'
import { User } from '../types'
import Icon from '../components/Icon'
import Modal from '../components/Modal'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { useConfirm } from '../components/ConfirmDialog'
import { useAuth } from '../contexts/AuthContext'
import { useDebounce } from '../hooks/useDebounce'

const ROLES: Array<{ value: User['role']; label: string; description: string }> = [
  { value: 'ADMIN', label: 'Admin', description: 'Full system access, user management' },
  { value: 'STAFF', label: 'Staff', description: 'Patient management, scheduling, call handling' },
  { value: 'DOCTOR', label: 'Doctor', description: 'Own profile and slot management' },
  { value: 'READONLY', label: 'Read-Only', description: 'View-only access for auditors' },
]

const roleBadge = (role: User['role']): string => {
  switch (role) {
    case 'ADMIN':
      return 'badge-danger'
    case 'STAFF':
      return 'badge-info'
    case 'DOCTOR':
      return 'badge-success'
    case 'READONLY':
      return 'badge-secondary'
  }
}

const avatarColor = (id: number) => `em-${((id - 1) % 6) + 1}` as const

const passwordStrength = (pw: string): { score: 0 | 1 | 2 | 3 | 4; label: string } => {
  let score = 0
  if (pw.length >= 8) score++
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++
  if (/\d/.test(pw)) score++
  if (/[^\w\s]/.test(pw)) score++
  const labels = ['Too short', 'Weak', 'Fair', 'Good', 'Strong']
  return { score: score as 0 | 1 | 2 | 3 | 4, label: labels[score] }
}

const UsersPage: React.FC = () => {
  const toast = useToast()
  const confirm = useConfirm()
  const { user: currentUser } = useAuth()

  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 250)

  // Modal state
  const [showCreate, setShowCreate] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [saving, setSaving] = useState(false)

  const [form, setForm] = useState<UserCreateData>({
    email: '',
    username: '',
    first_name: '',
    last_name: '',
    role: 'STAFF',
    password: '',
    password_confirm: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [formError, setFormError] = useState<string>('')

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true)
      const data = await userService.listUsers()
      setUsers(data)
      setError('')
    } catch (err: any) {
      const detail =
        err.response?.status === 403
          ? 'Only administrators can manage users.'
          : err.response?.data?.detail || err.message || 'Failed to load users'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const openCreate = () => {
    setForm({
      email: '',
      username: '',
      first_name: '',
      last_name: '',
      role: 'STAFF',
      password: '',
      password_confirm: '',
    })
    setFormError('')
    setShowCreate(true)
  }

  const openEdit = (user: User) => {
    setEditingUser(user)
    setFormError('')
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')

    if (form.password !== form.password_confirm) {
      setFormError("Passwords don't match")
      return
    }
    if (form.password.length < 8) {
      setFormError('Password must be at least 8 characters')
      return
    }

    try {
      setSaving(true)
      const created = await userService.createUser(form)
      setUsers((prev) => [created, ...prev])
      toast.success('User created', `${created.email} has been added as ${created.role_display}.`)
      setShowCreate(false)
    } catch (err: any) {
      const data = err.response?.data
      if (data) {
        const firstField = Object.keys(data)[0]
        const firstMsg = Array.isArray(data[firstField]) ? data[firstField][0] : data[firstField]
        setFormError(`${firstField}: ${firstMsg}`)
      } else {
        setFormError(err.message || 'Failed to create user')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingUser) return
    setFormError('')
    try {
      setSaving(true)
      const updated = await userService.updateUser(editingUser.id, {
        first_name: editingUser.first_name,
        last_name: editingUser.last_name,
        role: editingUser.role,
        is_active: editingUser.is_active,
      })
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
      toast.success('User updated', `${updated.email} has been saved.`)
      setEditingUser(null)
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to update user')
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (user: User) => {
    if (user.id === currentUser?.id) {
      toast.warning('Not allowed', "You can't deactivate your own account.")
      return
    }
    const willActivate = !user.is_active
    if (!willActivate) {
      const ok = await confirm({
        title: `Deactivate ${user.email}?`,
        message: 'They will lose access immediately. You can reactivate them at any time.',
        confirmLabel: 'Deactivate',
        variant: 'danger',
      })
      if (!ok) return
    }
    try {
      const updated = await userService.updateUser(user.id, { is_active: willActivate })
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
      toast.success(updated.is_active ? 'User reactivated' : 'User deactivated', updated.email)
    } catch (err: any) {
      toast.error('Update failed', err.response?.data?.detail || err.message)
    }
  }

  const filtered = users.filter((u) => {
    if (roleFilter && u.role !== roleFilter) return false
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase()
      return (
        u.email.toLowerCase().includes(q) ||
        u.full_name.toLowerCase().includes(q) ||
        u.username.toLowerCase().includes(q)
      )
    }
    return true
  })

  // Belt-and-braces: route guard already prevents non-admins, but render a friendly fallback too
  if (currentUser && currentUser.role !== 'ADMIN') {
    return (
      <div className="page-container">
        <Breadcrumbs />
        <EmptyState
          icon="lock"
          title="Administrator access required"
          description="You need an Admin role to manage users."
        />
      </div>
    )
  }

  const pwStrength = passwordStrength(form.password)
  const hasFilters = !!debouncedSearch || !!roleFilter
  const isEmpty = !loading && !error && filtered.length === 0

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>Users &amp; access</h1>
          <p>
            {users.length} team member{users.length === 1 ? '' : 's'} · invite staff, doctors, and auditors.
          </p>
        </div>
        <Button variant="primary" onClick={openCreate} leftIcon={<Icon name="user-plus" size={16} />}>
          Invite user
        </Button>
      </div>

      {error && (
        <ErrorState
          inline
          title="Couldn't load users"
          message={error}
          onRetry={fetchUsers}
          retrying={loading}
        />
      )}

      <div className="table-wrap">
        <div className="table-tools">
          <div style={{ position: 'relative', flex: 1, maxWidth: 420 }}>
            <label htmlFor="users-search" className="visually-hidden">
              Search users
            </label>
            <input
              id="users-search"
              type="search"
              className="form-input"
              style={{ paddingLeft: 36 }}
              placeholder="Search by name, email, or username…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                left: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--muted-2)',
              }}
            >
              <Icon name="search" size={16} />
            </span>
          </div>
          <div className="pill-filter" role="radiogroup" aria-label="Filter by role">
            {[
              { val: '', label: 'All' },
              { val: 'ADMIN', label: 'Admin' },
              { val: 'STAFF', label: 'Staff' },
              { val: 'DOCTOR', label: 'Doctor' },
              { val: 'READONLY', label: 'Read-only' },
            ].map((r) => (
              <button
                key={r.val}
                role="radio"
                aria-checked={roleFilter === r.val}
                className={roleFilter === r.val ? 'active' : ''}
                onClick={() => setRoleFilter(r.val)}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 0 }}>
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                style={{
                  padding: '16px 20px',
                  borderBottom: '1px solid var(--border)',
                  display: 'flex',
                  gap: 12,
                  alignItems: 'center',
                }}
              >
                <Skeleton circle width={32} height={32} />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <Skeleton width="40%" height={14} />
                  <Skeleton width="25%" height={10} />
                </div>
                <Skeleton width={60} height={20} />
              </div>
            ))}
          </div>
        ) : isEmpty ? (
          <EmptyState
            icon="users"
            title={hasFilters ? 'No users match' : 'No users yet'}
            description={
              hasFilters
                ? 'Try clearing filters or invite a new team member.'
                : 'Invite your first team member to get started.'
            }
            action={
              hasFilters ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearch('')
                    setRoleFilter('')
                  }}
                >
                  Clear filters
                </Button>
              ) : (
                <Button
                  variant="primary"
                  onClick={openCreate}
                  leftIcon={<Icon name="user-plus" size={16} />}
                >
                  Invite user
                </Button>
              )
            }
          />
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">User</th>
                  <th scope="col">Role</th>
                  <th scope="col">Status</th>
                  <th scope="col">Joined</th>
                  <th scope="col" style={{ width: 100 }}>
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => {
                  const isSelf = u.id === currentUser?.id
                  return (
                    <tr key={u.id}>
                      <td>
                        <div className="cell-user">
                          <span className={`avatar ${avatarColor(u.id)}`} aria-hidden="true">
                            {(u.first_name?.[0] || u.email[0]).toUpperCase()}
                            {(u.last_name?.[0] || '').toUpperCase()}
                          </span>
                          <div>
                            <div className="cell-user-name">
                              {u.full_name || u.email}
                              {isSelf && (
                                <span className="badge badge-primary" style={{ marginLeft: 8 }}>
                                  You
                                </span>
                              )}
                            </div>
                            <div className="cell-user-sub">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${roleBadge(u.role)}`}>
                          {u.role_display || u.role}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${u.is_active ? 'badge-success' : 'badge-secondary'}`}
                        >
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="small-muted">
                        {new Date(u.date_joined).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td>
                        <div className="d-flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            onClick={() => openEdit(u)}
                            aria-label={`Edit ${u.email}`}
                            leftIcon={<Icon name="edit" size={14} />}
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            iconOnly
                            onClick={() => toggleActive(u)}
                            disabled={isSelf}
                            aria-label={
                              isSelf
                                ? `Cannot change your own status`
                                : u.is_active
                                  ? `Deactivate ${u.email}`
                                  : `Reactivate ${u.email}`
                            }
                            leftIcon={<Icon name={u.is_active ? 'x' : 'check'} size={14} />}
                          />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Modal */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Invite new user"
        description="Create an account with role-based access. They'll log in with the email and password you set."
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreate(false)} disabled={saving}>
              Cancel
            </Button>
            <Button
              type="submit"
              form="create-user-form"
              variant="primary"
              loading={saving}
              leftIcon={!saving && <Icon name="user-plus" size={16} />}
            >
              Create user
            </Button>
          </>
        }
      >
        <form id="create-user-form" onSubmit={handleCreate}>
          {formError && (
            <div className="alert alert-error" role="alert">
              <Icon name="x" size={16} />
              <span>{formError}</span>
            </div>
          )}

          <div className="row g-3">
            <div className="col-md-6">
              <div className="form-group">
                <label htmlFor="u-first" className="form-label">
                  First name
                </label>
                <input
                  id="u-first"
                  className="form-input"
                  required
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                />
              </div>
            </div>
            <div className="col-md-6">
              <div className="form-group">
                <label htmlFor="u-last" className="form-label">
                  Last name
                </label>
                <input
                  id="u-last"
                  className="form-input"
                  required
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                />
              </div>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="u-email" className="form-label">
              Email address
            </label>
            <input
              id="u-email"
              type="email"
              className="form-input"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label htmlFor="u-username" className="form-label">
              Username
            </label>
            <input
              id="u-username"
              className="form-input"
              required
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              placeholder="shortname"
            />
          </div>

          <div className="form-group">
            <span className="form-label" id="u-role-label">
              Role
            </span>
            <div role="radiogroup" aria-labelledby="u-role-label" style={{ display: 'grid', gap: 8 }}>
              {ROLES.map((r) => (
                <label key={r.value} className={`role-card ${form.role === r.value ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="role"
                    checked={form.role === r.value}
                    onChange={() => setForm({ ...form, role: r.value })}
                  />
                  <div>
                    <div className="role-card-title">{r.label}</div>
                    <div className="role-card-desc">{r.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="u-pw" className="form-label">
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="u-pw"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                style={{ paddingRight: 40 }}
                required
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                autoComplete="new-password"
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: 8,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 0,
                  color: 'var(--muted)',
                  cursor: 'pointer',
                  padding: 6,
                  borderRadius: 4,
                }}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                <Icon name={showPassword ? 'eye-off' : 'eye'} size={14} />
              </button>
            </div>
            {form.password && (
              <>
                <div className="pw-bar">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="pw-seg"
                      style={{
                        background:
                          i < pwStrength.score
                            ? pwStrength.score >= 3
                              ? 'var(--brand)'
                              : pwStrength.score === 2
                                ? '#F59E0B'
                                : 'var(--danger)'
                            : 'var(--border)',
                      }}
                    />
                  ))}
                </div>
                <div className="pw-hint">{pwStrength.label} · minimum 8 characters</div>
              </>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="u-pw2" className="form-label">
              Confirm password
            </label>
            <input
              id="u-pw2"
              type={showPassword ? 'text' : 'password'}
              className="form-input"
              required
              value={form.password_confirm}
              onChange={(e) => setForm({ ...form, password_confirm: e.target.value })}
              autoComplete="new-password"
            />
          </div>
        </form>
      </Modal>

      {/* Edit Modal */}
      {editingUser && (
        <Modal
          open={true}
          onClose={() => setEditingUser(null)}
          title={`Edit ${editingUser.email}`}
          description="Update role and status. Password resets require the user to contact an admin."
          footer={
            <>
              <Button variant="ghost" onClick={() => setEditingUser(null)} disabled={saving}>
                Cancel
              </Button>
              <Button type="submit" form="edit-user-form" variant="primary" loading={saving}>
                Save changes
              </Button>
            </>
          }
        >
          <form id="edit-user-form" onSubmit={handleUpdate}>
            {formError && (
              <div className="alert alert-error" role="alert">
                <Icon name="x" size={16} />
                <span>{formError}</span>
              </div>
            )}
            <div className="row g-3">
              <div className="col-md-6">
                <div className="form-group">
                  <label htmlFor="e-first" className="form-label">
                    First name
                  </label>
                  <input
                    id="e-first"
                    className="form-input"
                    value={editingUser.first_name}
                    onChange={(e) => setEditingUser({ ...editingUser, first_name: e.target.value })}
                  />
                </div>
              </div>
              <div className="col-md-6">
                <div className="form-group">
                  <label htmlFor="e-last" className="form-label">
                    Last name
                  </label>
                  <input
                    id="e-last"
                    className="form-input"
                    value={editingUser.last_name}
                    onChange={(e) => setEditingUser({ ...editingUser, last_name: e.target.value })}
                  />
                </div>
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="e-role" className="form-label">
                Role
              </label>
              <select
                id="e-role"
                className="form-select"
                value={editingUser.role}
                onChange={(e) =>
                  setEditingUser({ ...editingUser, role: e.target.value as User['role'] })
                }
                disabled={editingUser.id === currentUser?.id}
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label} — {r.description}
                  </option>
                ))}
              </select>
              {editingUser.id === currentUser?.id && (
                <div className="pw-hint">You can't change your own role.</div>
              )}
            </div>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={editingUser.is_active}
                  onChange={(e) =>
                    setEditingUser({ ...editingUser, is_active: e.target.checked })
                  }
                  disabled={editingUser.id === currentUser?.id}
                />
                <span style={{ fontSize: '0.875rem', color: 'var(--ink)' }}>
                  Account is active
                </span>
              </label>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

export default UsersPage

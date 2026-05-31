import React, { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import Icon from '../components/Icon'
import Button from '../components/Button'
import Breadcrumbs from '../components/Breadcrumbs'
import { Skeleton } from '../components/Skeleton'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../components/Toast'
import { userService } from '../services/userService'

interface FormValues {
  first_name: string
  last_name: string
  email: string
}

const ProfilePage: React.FC = () => {
  const { user, refresh, loading } = useAuth()
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormValues>({
    defaultValues: { first_name: '', last_name: '', email: '' },
  })

  useEffect(() => {
    if (user) {
      reset({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
      })
    }
  }, [user, reset])

  const onSubmit = handleSubmit(async (values) => {
    if (!user) return
    setSubmitting(true)
    try {
      await userService.updateUser(user.id, values)
      toast.success('Profile updated', 'Your details have been saved.')
      await refresh()
    } catch (err: any) {
      toast.error(
        'Update failed',
        err.response?.data?.detail || 'You may not have permission to edit this profile.'
      )
    } finally {
      setSubmitting(false)
    }
  })

  const initials = (user?.email || 'U')
    .split('@')[0]
    .split(/[._-]/)
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="page-container">
      <Breadcrumbs />
      <div className="page-heading">
        <div>
          <h1>My profile</h1>
          <p>Update your personal details and review account permissions.</p>
        </div>
      </div>

      <div className="row">
        <div className="col-md-4">
          <div className="card">
            <div className="card-body" style={{ textAlign: 'center', padding: '32px 20px' }}>
              <div
                className="sidebar-user-avatar"
                style={{ width: 72, height: 72, fontSize: 24, margin: '0 auto 12px' }}
              >
                {initials}
              </div>
              {loading || !user ? (
                <>
                  <Skeleton width={140} height={18} />
                  <div style={{ marginTop: 8 }}>
                    <Skeleton width={100} height={12} />
                  </div>
                </>
              ) : (
                <>
                  <h4 style={{ marginBottom: 4 }}>{user.full_name || user.email}</h4>
                  <div className="small-muted">{user.email}</div>
                  <div style={{ marginTop: 12 }}>
                    <span className="badge badge-primary">
                      <Icon name="shield" size={10} /> {user.role_display || user.role}
                    </span>
                  </div>
                  <div className="small-muted mt-3">
                    Joined{' '}
                    {new Date(user.date_joined).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'long',
                    })}
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="card mt-4">
            <div className="card-head">
              <h5>Permissions</h5>
            </div>
            <div className="card-body" style={{ display: 'grid', gap: 8, fontSize: '0.875rem' }}>
              <PermissionRow ok={user?.role === 'ADMIN'} label="Manage users" />
              <PermissionRow ok={user?.role === 'ADMIN'} label="Manage doctors" />
              <PermissionRow
                ok={user?.role === 'ADMIN' || user?.role === 'STAFF'}
                label="Manage patients"
              />
              <PermissionRow
                ok={user?.role === 'ADMIN' || user?.role === 'STAFF'}
                label="Book appointments"
              />
              <PermissionRow
                ok={user?.role === 'ADMIN' || user?.role === 'DOCTOR'}
                label="Manage availability"
              />
              <PermissionRow ok label="View dashboards" />
            </div>
          </div>
        </div>

        <div className="col-md-8">
          <div className="card">
            <div className="card-head">
              <div>
                <h5>Personal details</h5>
                <p>Changes apply immediately after saving.</p>
              </div>
            </div>
            <div className="card-body">
              <form onSubmit={onSubmit}>
                <div className="row g-3">
                  <div className="col-md-6">
                    <label htmlFor="first_name" className="form-label">
                      First name
                    </label>
                    <input
                      id="first_name"
                      className="form-input"
                      {...register('first_name', { required: 'First name is required' })}
                    />
                    {errors.first_name && (
                      <div className="form-error">{errors.first_name.message}</div>
                    )}
                  </div>
                  <div className="col-md-6">
                    <label htmlFor="last_name" className="form-label">
                      Last name
                    </label>
                    <input
                      id="last_name"
                      className="form-input"
                      {...register('last_name', { required: 'Last name is required' })}
                    />
                    {errors.last_name && (
                      <div className="form-error">{errors.last_name.message}</div>
                    )}
                  </div>
                  <div className="col-md-12">
                    <label htmlFor="email" className="form-label">
                      Email
                    </label>
                    <input
                      id="email"
                      type="email"
                      className="form-input"
                      {...register('email', {
                        required: 'Email is required',
                        pattern: {
                          value: /^\S+@\S+\.\S+$/,
                          message: 'Enter a valid email',
                        },
                      })}
                    />
                    {errors.email && <div className="form-error">{errors.email.message}</div>}
                  </div>
                </div>

                <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={!isDirty || submitting}
                    onClick={() =>
                      user &&
                      reset({
                        first_name: user.first_name || '',
                        last_name: user.last_name || '',
                        email: user.email || '',
                      })
                    }
                  >
                    Reset
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    loading={submitting}
                    disabled={!isDirty}
                  >
                    Save changes
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const PermissionRow: React.FC<{ ok?: boolean; label: string }> = ({ ok, label }) => (
  <div className="d-flex justify-content-between align-items-center">
    <span style={{ color: 'var(--ink-2)' }}>{label}</span>
    <span
      className={`badge ${ok ? 'badge-success' : 'badge-secondary'}`}
      style={{ minWidth: 64, justifyContent: 'center' }}
    >
      {ok ? 'Allowed' : 'Restricted'}
    </span>
  </div>
)

export default ProfilePage

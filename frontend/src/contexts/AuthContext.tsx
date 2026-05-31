import React, { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import { User } from '../types'
import { getCurrentUser } from '../services/authService'

type Role = User['role']

interface AuthContextValue {
  user: User | null
  loading: boolean
  refresh: () => Promise<void>
  setUser: (u: User | null) => void
  signOut: () => void
  hasRole: (...roles: Role[]) => boolean
  can: (
    action:
      | 'manage_patients'
      | 'manage_doctors'
      | 'manage_users'
      | 'manage_slots'
      | 'book_slots'
      | 'edit_own_profile'
  ) => boolean
  isAdmin: boolean
  isStaff: boolean
  isDoctor: boolean
  isReadOnly: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

const readStoredUser = (): User | null => {
  try {
    const raw = localStorage.getItem('user')
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' && parsed.email ? (parsed as User) : null
  } catch {
    return null
  }
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUserState] = useState<User | null>(readStoredUser)
  const [loading, setLoading] = useState(false)

  const setUser = useCallback((u: User | null) => {
    setUserState(u)
    if (u) localStorage.setItem('user', JSON.stringify(u))
    else localStorage.removeItem('user')
  }, [])

  const refresh = useCallback(async () => {
    if (!localStorage.getItem('access_token')) return
    setLoading(true)
    try {
      const me = await getCurrentUser()
      setUser(me)
    } catch {
      // 401 handled by api interceptor
    } finally {
      setLoading(false)
    }
  }, [setUser])

  useEffect(() => {
    if (localStorage.getItem('access_token') && !user) {
      refresh()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const signOut = useCallback(() => {
    localStorage.clear()
    setUserState(null)
    window.location.href = '/login'
  }, [])

  const hasRole = useCallback(
    (...roles: Role[]) => !!user && roles.includes(user.role),
    [user]
  )

  const can: AuthContextValue['can'] = useCallback(
    (action) => {
      if (!user) return false
      switch (action) {
        case 'manage_patients':
          return user.role === 'ADMIN' || user.role === 'STAFF'
        case 'manage_doctors':
          return user.role === 'ADMIN'
        case 'manage_users':
          return user.role === 'ADMIN'
        case 'manage_slots':
          return user.role === 'ADMIN' || user.role === 'DOCTOR'
        case 'book_slots':
          return user.role === 'ADMIN' || user.role === 'STAFF'
        case 'edit_own_profile':
          return true
      }
    },
    [user]
  )

  const value: AuthContextValue = {
    user,
    loading,
    refresh,
    setUser,
    signOut,
    hasRole,
    can,
    isAdmin: user?.role === 'ADMIN',
    isStaff: user?.role === 'STAFF',
    isDoctor: user?.role === 'DOCTOR',
    isReadOnly: user?.role === 'READONLY',
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

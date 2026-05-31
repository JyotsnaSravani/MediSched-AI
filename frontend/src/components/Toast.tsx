import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import Icon from './Icon'

type ToastType = 'success' | 'error' | 'info' | 'warning'

interface Toast {
  id: number
  type: ToastType
  title: string
  message?: string
}

interface ToastContextValue {
  show: (type: ToastType, title: string, message?: string) => void
  success: (title: string, message?: string) => void
  error: (title: string, message?: string) => void
  info: (title: string, message?: string) => void
  warning: (title: string, message?: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export const useToast = (): ToastContextValue => {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}

const iconOf: Record<ToastType, 'check' | 'x' | 'bell' | 'sparkles'> = {
  success: 'check',
  error: 'x',
  info: 'bell',
  warning: 'sparkles',
}

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const show = useCallback(
    (type: ToastType, title: string, message?: string) => {
      const id = Date.now() + Math.random()
      setToasts((prev) => [...prev, { id, type, title, message }])
      setTimeout(() => dismiss(id), 4500)
    },
    [dismiss]
  )

  const value: ToastContextValue = {
    show,
    success: (title, message) => show('success', title, message),
    error: (title, message) => show('error', title, message),
    info: (title, message) => show('info', title, message),
    warning: (title, message) => show('warning', title, message),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`} role="status">
            <span className="toast-icon">
              <Icon name={iconOf[t.type]} size={14} />
            </span>
            <div className="toast-body">
              <div className="toast-title">{t.title}</div>
              {t.message && <div className="toast-message">{t.message}</div>}
            </div>
            <button className="toast-dismiss" onClick={() => dismiss(t.id)} aria-label="Dismiss">
              <Icon name="x" size={12} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

import React, { createContext, useCallback, useContext, useState, ReactNode } from 'react'
import Modal from './Modal'
import Button from './Button'

interface ConfirmOptions {
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'primary' | 'danger' | 'warning'
}

type ConfirmFn = (opts: ConfirmOptions) => Promise<boolean>

const ConfirmContext = createContext<ConfirmFn | null>(null)

export const useConfirm = (): ConfirmFn => {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used inside <ConfirmProvider>')
  return ctx
}

interface State extends ConfirmOptions {
  open: boolean
  resolve?: (v: boolean) => void
}

export const ConfirmProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<State>({ open: false, title: '' })

  const confirm: ConfirmFn = useCallback((opts) => {
    return new Promise<boolean>((resolve) => {
      setState({ ...opts, open: true, resolve })
    })
  }, [])

  const close = (result: boolean) => {
    state.resolve?.(result)
    setState((s) => ({ ...s, open: false, resolve: undefined }))
  }

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Modal
        open={state.open}
        onClose={() => close(false)}
        title={state.title}
        description={state.message}
        footer={
          <>
            <Button variant="ghost" onClick={() => close(false)}>
              {state.cancelLabel ?? 'Cancel'}
            </Button>
            <Button
              variant={state.variant === 'danger' ? 'danger' : 'primary'}
              onClick={() => close(true)}
              autoFocus
            >
              {state.confirmLabel ?? 'Confirm'}
            </Button>
          </>
        }
      >
        {/* Body intentionally empty — message shown in head description */}
        <span className="visually-hidden">{state.message}</span>
      </Modal>
    </ConfirmContext.Provider>
  )
}

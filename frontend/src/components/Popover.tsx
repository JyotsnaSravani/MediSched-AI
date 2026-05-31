import React, { ReactNode, useEffect, useRef } from 'react'

interface Props {
  open: boolean
  onClose: () => void
  anchorRef: React.RefObject<HTMLElement>
  children: ReactNode
  align?: 'left' | 'right'
  width?: number
  ariaLabel?: string
}

const Popover: React.FC<Props> = ({
  open,
  onClose,
  anchorRef,
  children,
  align = 'right',
  width = 320,
  ariaLabel,
}) => {
  const popRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      const t = e.target as Node
      if (popRef.current?.contains(t) || anchorRef.current?.contains(t)) return
      onClose()
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose, anchorRef])

  if (!open) return null

  return (
    <div
      ref={popRef}
      className="popover"
      role="dialog"
      aria-label={ariaLabel}
      style={{
        width,
        right: align === 'right' ? 0 : 'auto',
        left: align === 'left' ? 0 : 'auto',
      }}
    >
      {children}
    </div>
  )
}

export default Popover

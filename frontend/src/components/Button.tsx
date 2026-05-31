import React, { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'warning'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  iconOnly?: boolean
  full?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  loading = false,
  iconOnly = false,
  full = false,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  children,
  ...rest
}) => {
  const cls = [
    'btn',
    `btn-${variant}`,
    size === 'sm' ? 'btn-sm' : size === 'lg' ? 'btn-lg' : '',
    iconOnly ? 'btn-icon' : '',
    full ? 'btn-full' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button
      className={cls}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <span
          className={`spinner ${variant === 'primary' || variant === 'danger' || variant === 'success' || variant === 'warning' ? 'spinner-on-dark' : ''}`}
          aria-hidden="true"
        />
      ) : (
        leftIcon
      )}
      {!iconOnly && children}
      {!loading && rightIcon}
    </button>
  )
}

export default Button

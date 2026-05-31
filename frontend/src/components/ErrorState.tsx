import React from 'react'
import Icon from './Icon'
import Button from './Button'

interface ErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
  retrying?: boolean
  inline?: boolean
}

const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message,
  onRetry,
  retrying = false,
  inline = false,
}) => {
  if (inline) {
    return (
      <div className="alert alert-error" role="alert" aria-live="assertive">
        <Icon name="x" size={16} />
        <div style={{ flex: 1 }}>
          <strong>{title}</strong>
          {message && <div style={{ marginTop: 2 }}>{message}</div>}
        </div>
        {onRetry && (
          <Button size="sm" variant="secondary" onClick={onRetry} loading={retrying}>
            Retry
          </Button>
        )}
      </div>
    )
  }

  return (
    <div className="empty-state" role="alert" aria-live="assertive">
      <Icon name="x" size={48} />
      <h4>{title}</h4>
      {message && <p>{message}</p>}
      {onRetry && (
        <div style={{ marginTop: 16 }}>
          <Button variant="primary" onClick={onRetry} loading={retrying}>
            Try again
          </Button>
        </div>
      )}
    </div>
  )
}

export default ErrorState

import React, { ReactNode } from 'react'
import Icon from './Icon'

interface EmptyStateProps {
  icon?: Parameters<typeof Icon>[0]['name']
  title: string
  description?: string
  action?: ReactNode
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon = 'inbox',
  title,
  description,
  action,
}) => (
  <div className="empty-state" role="status">
    <Icon name={icon} size={48} />
    <h4>{title}</h4>
    {description && <p>{description}</p>}
    {action && <div style={{ marginTop: 16 }}>{action}</div>}
  </div>
)

export default EmptyState

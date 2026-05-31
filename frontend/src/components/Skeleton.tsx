import React from 'react'

interface SkeletonProps {
  width?: number | string
  height?: number | string
  circle?: boolean
  className?: string
  style?: React.CSSProperties
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = 14,
  circle = false,
  className = '',
  style,
}) => (
  <span
    className={`skeleton ${className}`}
    aria-hidden="true"
    style={{
      width,
      height,
      borderRadius: circle ? '50%' : undefined,
      ...style,
    }}
  />
)

export const SkeletonText: React.FC<{ lines?: number; width?: string }> = ({
  lines = 3,
  width = '100%',
}) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        height={12}
        width={i === lines - 1 ? '70%' : width}
      />
    ))}
  </div>
)

export const SkeletonRow: React.FC<{ columns: number }> = ({ columns }) => (
  <tr>
    {Array.from({ length: columns }).map((_, i) => (
      <td key={i}>
        <Skeleton height={14} />
      </td>
    ))}
  </tr>
)

export default Skeleton

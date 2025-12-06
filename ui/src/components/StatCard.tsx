import { ReactNode } from 'react'

interface StatCardProps {
  title: string
  value: string | number
  icon: ReactNode
  subtitle?: string
  color?: 'default' | 'success' | 'warning' | 'error'
}

const colorClasses = {
  default: 'border-surface-light',
  success: 'border-success/30',
  warning: 'border-warning/30',
  error: 'border-error/30',
}

const textClasses = {
  default: 'text-white',
  success: 'text-success',
  warning: 'text-warning',
  error: 'text-error',
}

export default function StatCard({
  title,
  value,
  icon,
  subtitle,
  color = 'default'
}: StatCardProps) {
  return (
    <div className={`
      bg-surface rounded-xl p-6 border-2 ${colorClasses[color]}
      transition-all hover:scale-[1.02]
    `}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className={`text-3xl font-bold mt-1 ${textClasses[color]}`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-gray-500 text-sm mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg bg-surface-light ${textClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

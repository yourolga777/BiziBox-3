import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
}

function Card({ title, children, className = '' }: CardProps) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-4 ${className}`}>
      {title && <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>}
      {children}
    </div>
  )
}

export default Card

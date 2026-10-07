import { memo, useState, useEffect } from 'react'
import { AlertCircle, RefreshCw, TrendingUp, TrendingDown, Mail, ListTodo, CircleCheck, MessageSquareText } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../common/Card'
import { useDashboardMetricsQuery } from '../../hooks/queries'
import type { MetricsResponse } from '../../types/dashboard'

interface MetricCardProps {
  icon: typeof Mail
  label: string
  value: number
  yesterday: number
  total: number
  color: string
  linkTo: string
  subtitle?: string
  hideTrend?: boolean
}

const MetricCard = memo(function MetricCard({ icon: Icon, label, value, yesterday, total, color, linkTo, subtitle = 'сегодня', hideTrend }: MetricCardProps) {
  const diff = value - yesterday
  const up = diff >= 0
  return (
    <Link to={linkTo} className="block group relative">
      <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3 transition-all duration-200 group-hover:scale-[1.02] group-hover:shadow-lg">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${color}15` }}>
          <Icon size={20} style={{ color }} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold text-gray-900 leading-tight">{value}</p>
          <p className="text-[11px] text-gray-400">{subtitle}</p>
        </div>
        {!hideTrend && (
          <div className={`flex items-center gap-0.5 ${up ? 'text-green-600' : 'text-red-500'}`}>
            {up ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            <span className="text-xs font-semibold">{Math.abs(diff)}</span>
          </div>
        )}
      </div>
      <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2.5 py-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 shadow-lg">
        Всего: {total} &middot; {subtitle === 'сегодня' ? `За сегодня: ${value}` : `Активных: ${value}`} &middot; Вчера: {yesterday}
      </div>
    </Link>
  )
})

const ACHIEVEMENT_CYCLES = [
  { key: 'answered', label: 'Отвечено', icon: MessageSquareText, color: '#6366f1', getValue: (d: MetricsResponse) => d.answered_messages },
  { key: 'completed', label: 'Закрыто', icon: CircleCheck, color: '#f59e0b', getValue: (d: MetricsResponse) => d.completed_tasks },
]

const PULSE_CYCLES = [
  {
    key: 'messages',
    label: 'Новые сообщения',
    icon: Mail,
    color: '#6366f1',
    getValue: (d: MetricsResponse) => d.new_messages,
  },
  {
    key: 'tasks',
    label: 'Новые задачи',
    icon: ListTodo,
    color: '#f59e0b',
    getValue: (d: MetricsResponse) => d.new_tasks,
  },
]

const PulseCircle = memo(function PulseCircle({
  value,
  color,
  pulseDuration,
}: {
  value: number
  color: string
  pulseDuration: string
}) {
  return (
    <div className="relative w-20 h-20">
      <svg
        className="w-20 h-20 animate-heartbeat"
        style={{ '--pulse-duration': pulseDuration } as React.CSSProperties}
        viewBox="0 0 80 80"
      >
        <circle cx="40" cy="40" r="34" fill="none" stroke="#e5e7eb" strokeWidth="3" />
        <circle
          cx="40" cy="40" r="34"
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={`${Math.min(value / 50, 1) * 220} 220`}
          transform="rotate(-90 40 40)"
          className="transition-all duration-700"
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-lg font-bold"
        style={{ color }}
      >
        {value}
      </span>
    </div>
  )
})

function PulseWidget() {
  const { data, isLoading, error, refetch } = useDashboardMetricsQuery(30000)
  const [cycleIndex, setCycleIndex] = useState(0)
  const [achievementIndex, setAchievementIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCycleIndex((prev) => (prev + 1) % PULSE_CYCLES.length)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setAchievementIndex((prev) => (prev + 1) % ACHIEVEMENT_CYCLES.length)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <Card className="flex-1">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-gray-200 animate-pulse shrink-0" />
          <div className="grid grid-cols-2 gap-3 flex-1">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
          <div className="w-20 h-20 rounded-full bg-gray-200 animate-pulse shrink-0" />
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card title="Пульс" className="flex-1">
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <AlertCircle className="text-red-500" size={32} />
          <p className="text-gray-600">{error instanceof Error ? error.message : 'Ошибка загрузки'}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
          >
            <RefreshCw size={14} />
            Повторить
          </button>
        </div>
      </Card>
    )
  }

  if (!data) return null

  const { intensity: apiIntensity } = data.pulse_animation
  const pulseRate = typeof apiIntensity === 'number' ? Math.max(0, Math.min(1, apiIntensity)) : 0.5
  const pulseDuration = `${2.5 - pulseRate * 1.5}s`

  const aCycle = ACHIEVEMENT_CYCLES[achievementIndex]
  const aValue = aCycle.getValue(data)
  const AIcon = aCycle.icon

  const pCycle = PULSE_CYCLES[cycleIndex]
  const pValue = pCycle.getValue(data)
  const PIcon = pCycle.icon

  const updatedTime = new Date(data.last_updated).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })

  const items: MetricCardProps[] = [
    { icon: Mail, label: 'Сообщения', value: data.messages_today_active, yesterday: data.messages_yesterday, total: data.total_messages, color: '#6366f1', linkTo: '/inbox' },
    { icon: ListTodo, label: 'Задачи', value: data.active_tasks, yesterday: 0, total: data.total_tasks, color: '#f59e0b', linkTo: '/tasks', subtitle: 'не завершено', hideTrend: true },
  ]

  return (
    <Card className="flex-1">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Пульс</h3>
      <div className="flex flex-col xl:flex-row items-stretch xl:items-start gap-4">
        <div className="flex flex-col items-center gap-2 shrink-0 xl:w-24">
          <PulseCircle value={pValue} color={pCycle.color} pulseDuration={pulseDuration} />
          <div className="flex items-center gap-1.5">
            <PIcon size={14} style={{ color: pCycle.color }} />
            <span className="text-xs text-gray-500 font-medium">{pCycle.label}</span>
          </div>
          <p className="text-[11px] text-gray-400">за сегодня</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1 min-w-0">
          {items.map((item) => (
            <MetricCard key={item.label} {...item} />
          ))}
        </div>
        <div className="flex flex-col items-center gap-2 shrink-0 xl:w-24">
          <PulseCircle value={aValue} color={aCycle.color} pulseDuration={pulseDuration} />
          <div className="flex items-center gap-1.5">
            <AIcon size={14} style={{ color: aCycle.color }} />
            <span className="text-xs text-gray-500 font-medium">{aCycle.label}</span>
          </div>
          <p className="text-[11px] text-gray-400">за сегодня</p>
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-2 text-right">Обновлено: {updatedTime}</p>
    </Card>
  )
}

export default PulseWidget
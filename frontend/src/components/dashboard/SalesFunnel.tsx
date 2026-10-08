import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Card from '../common/Card'
import { useDashboardFunnelQuery } from '../../hooks/queries'
import { formatMoney } from '../../utils/format'

type Metric = 'count' | 'sum'
type Period = 'all' | 'week' | 'month'

const PERIODS: { value: Period; label: string }[] = [
  { value: 'all', label: 'Всё' },
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
]

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-500',
  in_progress: 'bg-amber-500',
  shipped: 'bg-violet-500',
  completed: 'bg-green-500',
}

function SalesFunnel() {
  const [metric, setMetric] = useState<Metric>('sum')
  const [period, setPeriod] = useState<Period>('all')
  const { data, isLoading } = useDashboardFunnelQuery(period)

  const stages = data?.stages ?? []
  const cancelled = data?.cancelled ?? 0

  const maxValue = useMemo(() => {
    const values = stages.map((s) => (metric === 'count' ? s.count : s.sum))
    return Math.max(1, ...values)
  }, [stages, metric])

  const isEmpty = stages.every((s) => s.count === 0)

  const valueOf = (s: { count: number; sum: number }) =>
    metric === 'count' ? s.count : s.sum

  const formatValue = (s: { count: number; sum: number }) =>
    metric === 'count' ? String(s.count) : formatMoney(s.sum)

  return (
    <Card title="Воронка продаж">
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <div className="inline-flex rounded-lg border border-gray-200 overflow-hidden">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-2.5 py-1 text-xs ${period === p.value ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="inline-flex rounded-lg border border-gray-200 overflow-hidden ml-auto">
          <button
            onClick={() => setMetric('count')}
            className={`px-2.5 py-1 text-xs ${metric === 'count' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            Кол-во
          </button>
          <button
            onClick={() => setMetric('sum')}
            className={`px-2.5 py-1 text-xs ${metric === 'sum' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            Сумма ₽
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-8 bg-gray-200 rounded-lg" />
          ))}
        </div>
      ) : isEmpty ? (
        <p className="text-sm text-gray-400 py-4 text-center">Нет заказов для воронки</p>
      ) : (
        <div className="space-y-1">
          {stages.map((stage, i) => {
            const value = valueOf(stage)
            const width = Math.max(2, Math.round((value / maxValue) * 100))
            const prev = i > 0 ? stages[i - 1] : null
            const prevValue = prev ? valueOf(prev) : 0
            const conversion = prev && prevValue > 0 ? Math.round((value / prevValue) * 100) : null
            return (
              <div key={stage.status}>
                {conversion !== null && (
                  <div className="text-[11px] text-gray-400 text-center leading-4">↓ {conversion}%</div>
                )}
                <Link to={`/orders?status=${stage.status}`} className="block group">
                  <div className="flex items-center gap-2">
                    <span className="w-24 text-xs text-gray-500 shrink-0 truncate">{stage.label}</span>
                    <div className="flex-1 h-6 bg-gray-100 rounded">
                      <div
                        className={`h-6 rounded ${STATUS_COLORS[stage.status] ?? 'bg-gray-400'}`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                    <span className="w-20 text-right text-xs font-medium text-gray-700 shrink-0">
                      {formatValue(stage)}
                    </span>
                  </div>
                </Link>
              </div>
            )
          })}
        </div>
      )}

      {cancelled > 0 && (
        <p className="text-xs text-gray-400 mt-3">Отменено: {cancelled}</p>
      )}
    </Card>
  )
}

export default SalesFunnel

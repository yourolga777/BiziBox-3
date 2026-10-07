import { useQuery } from '@tanstack/react-query'
import { fetchMetrics } from '../api/dashboard'

const METRICS_QUERY_KEY = ['dashboard', 'metrics'] as const
const REFETCH_INTERVAL_MS = 30_000

export function MetricsProvider({ children }: { children: React.ReactNode }) {
  // Provider сохранён для обратной совместимости с Layout.tsx.
  // Данные теперь хранятся в react-query, чтобы инвалидация обновляла badge сразу.
  return children
}

export function useMetrics() {
  return useQuery({
    queryKey: METRICS_QUERY_KEY,
    queryFn: fetchMetrics,
    refetchInterval: REFETCH_INTERVAL_MS,
    staleTime: 0,
  })
}

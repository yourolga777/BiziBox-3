import type { FunnelResponse, MetricsResponse } from '../types/dashboard'
import { request } from './client'

export async function fetchMetrics(): Promise<MetricsResponse> {
  return request<MetricsResponse>('/dashboard/metrics')
}

export async function fetchFunnel(period: string = 'all'): Promise<FunnelResponse> {
  return request<FunnelResponse>(`/dashboard/funnel?period=${period}`)
}

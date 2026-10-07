import type { MetricsResponse } from '../types/dashboard'
import { request } from './client'

export async function fetchMetrics(): Promise<MetricsResponse> {
  return request<MetricsResponse>('/dashboard/metrics')
}

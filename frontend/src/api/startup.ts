import type { StartupLoadResult } from '../types/startup'
import { request } from './client'

export const startupApi = {
  load: () =>
    request<StartupLoadResult>('/startup/load', {
      method: 'POST',
      _skipEnqueue: true,
      _timeoutMs: 8000,
    }),
}

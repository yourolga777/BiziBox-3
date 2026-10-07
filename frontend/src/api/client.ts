export { taskApi } from './tasks'
export { orderApi } from './orders'
export { productApi } from './products'
export { supplierApi } from './suppliers'
export { messageApi, sendReply } from './messages'
export { contactApi } from './contacts'
export { channelApi } from './channels'
export { fetchMetrics } from './dashboard'

const API_BASE = '/api'
export const BIZIBOX_LOGIN_KEY = 'bizibox_login'
const LOCAL_ONBOARDED_KEY = 'bizibox_onboarded_local'

export function getStoredLogin(): string | null {
  try {
    return localStorage.getItem(BIZIBOX_LOGIN_KEY)
  } catch {
    return null
  }
}

export function setStoredLogin(login: string | null) {
  try {
    if (login) {
      localStorage.setItem(BIZIBOX_LOGIN_KEY, login)
    } else {
      localStorage.removeItem(BIZIBOX_LOGIN_KEY)
    }
  } catch {
    // ignore
  }
}

export function isLocalOnboarded(): boolean {
  try {
    return localStorage.getItem(LOCAL_ONBOARDED_KEY) === '1'
  } catch {
    return false
  }
}

export function markLocalOnboarded() {
  try {
    localStorage.setItem(LOCAL_ONBOARDED_KEY, '1')
  } catch {
    // ignore
  }
}

export function clearLocalOnboarded() {
  try {
    localStorage.removeItem(LOCAL_ONBOARDED_KEY)
  } catch {
    // ignore
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class OfflineError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'OfflineError'
  }
}

const MUTATING_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

type RequestOptions = RequestInit & {
  _skipEnqueue?: boolean
  _offlineEnqueue?: boolean
  _timeoutMs?: number
  _entityId?: number
  _textResponse?: boolean
}

let enqueueOffline: ((method: string, path: string, body?: string, entityId?: number) => Promise<void>) | null = null

export function setOfflineEnqueue(fn: typeof enqueueOffline) {
  enqueueOffline = fn
}

export function isOfflineError(err: unknown): boolean {
  if (err instanceof OfflineError) return true
  if (err instanceof ApiError) {
    return err.status >= 500 && err.status <= 504
  }
  if (err instanceof DOMException && err.name === 'AbortError') return true
  if (err instanceof TypeError) return true
  return false
}

/**
 * Настоящее отсутствие соединения с сервером (в отличие от isOfflineError,
 * который дополнительно считает «офлайном» серверные 5xx). Используется там,
 * где 5xx нельзя маскировать под офлайн — например, при завершении онбординга.
 */
export function isConnectionError(err: unknown): boolean {
  if (err instanceof OfflineError) return true
  if (err instanceof DOMException && err.name === 'AbortError') return true
  if (err instanceof TypeError) return true
  return false
}

export interface OfflineEnqueued<T = unknown> {
  __offline: true
  localId: number
  entity: T
}

export async function requestOptimistic<T extends { id: number }>(
  path: string,
  options: RequestOptions,
  onOffline: () => Promise<T>,
): Promise<T | OfflineEnqueued<T>> {
  const requestOptions = { ...options, _skipEnqueue: true }

  if (!navigator.onLine) {
    const fake = await onOffline()
    return { __offline: true, localId: fake.id, entity: fake }
  }

  try {
    return await request<T>(path, requestOptions)
  } catch (err) {
    if (isOfflineError(err)) {
      const fake = await onOffline()
      return { __offline: true, localId: fake.id, entity: fake }
    }
    throw err
  }
}

export async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const method = (options?.method || 'GET').toUpperCase()
  const isMutation = MUTATING_METHODS.includes(method)
  const skipEnqueue = options?._skipEnqueue === true
  const offlineEnqueue = options?._offlineEnqueue !== false

  if (!skipEnqueue && offlineEnqueue && !navigator.onLine && isMutation && enqueueOffline) {
    await enqueueOffline(method, path, options?.body as string | undefined, options?._entityId)
    throw new OfflineError('Нет соединения с сервером. Запрос сохранён и будет отправлен при восстановлении связи')
  }

  let signal: AbortSignal | undefined
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  try {
    const controller = new AbortController()
    signal = controller.signal
    // MSW in jsdom cannot handle AbortSignal — skip in tests
    if (typeof process !== 'undefined' && (process.env as Record<string, string | undefined>)?.['NODE_ENV'] === 'test') {
      signal = undefined
    } else {
      timeoutId = setTimeout(() => controller.abort(), options?._timeoutMs ?? 15_000)
    }
  } catch {
    // AbortController not available
  }

  try {
    const isFormData = options?.body instanceof FormData
    const login = getStoredLogin()
    const headers: Record<string, string> = isFormData ? {} : { 'Content-Type': 'application/json' }
    if (login) {
      headers['X-Login'] = login
    }
    const fetchOptions: RequestInit = {
      ...options,
      headers: { ...headers, ...(options?.headers || {}) },
    }
    if (signal) fetchOptions.signal = signal
    const response = await fetch(`${API_BASE}${path}`, fetchOptions)
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(
        response.status,
        response.statusText,
        error.detail || response.statusText,
      )
    }
    if (response.status === 204) return undefined as T
    if (options?._textResponse) return (await response.text()) as T
    return response.json()
  } catch (err) {
    if (!skipEnqueue && offlineEnqueue && isMutation && enqueueOffline && isOfflineError(err)) {
      await enqueueOffline(method, path, options?.body as string | undefined, options?._entityId)
      throw new OfflineError('Нет соединения с сервером. Запрос сохранён и будет отправлен при восстановлении связи')
    }
    throw err
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
  }
}

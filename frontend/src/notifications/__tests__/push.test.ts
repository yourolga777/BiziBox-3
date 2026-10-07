import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getNotificationPermission,
  isPushSupported,
  requestNotificationPermission,
  subscribeToPush,
} from '../push'

describe('push notifications', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    // @ts-expect-error очищаем глобальные API
    delete window.Notification
    // @ts-expect-error очищаем PushManager
    delete window.PushManager
  })

  it('определяет отсутствие поддержки push (AC4 negative)', () => {
    expect(isPushSupported()).toBe(false)
  })

  it('возвращает unsupported для разрешения без Notification API', () => {
    expect(getNotificationPermission()).toBe('unsupported')
  })

  it('не запрашивает разрешение агрессивно, если push не поддерживается', async () => {
    const result = await requestNotificationPermission()
    expect(result).toBe('unsupported')
  })

  it('возвращает null при подписке без поддержки push', async () => {
    const sub = await subscribeToPush()
    expect(sub).toBeNull()
  })

  it('запрашивает разрешение только при поддержке Notification', async () => {
    const requestPermission = vi.fn().mockResolvedValue('granted')
    // @ts-expect-error мокаем Notification
    window.Notification = { permission: 'default', requestPermission }
    // @ts-expect-error мокаем PushManager
    window.PushManager = {}
    // @ts-expect-error мокаем serviceWorker
    navigator.serviceWorker = {}

    const result = await requestNotificationPermission()
    expect(requestPermission).toHaveBeenCalledTimes(1)
    expect(result).toBe('granted')
  })
})

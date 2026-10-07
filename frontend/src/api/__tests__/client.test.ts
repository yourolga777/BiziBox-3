import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, OfflineError, request, setOfflineEnqueue } from '../client'

const enqueue = vi.fn()
setOfflineEnqueue(enqueue)

let fetchMock: ReturnType<typeof vi.fn>

function setOnline(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true })
}

beforeEach(() => {
  setOnline(true)
  enqueue.mockReset()
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

describe('request — offline enqueue opt-out (_offlineEnqueue)', () => {
  it('by default enqueues mutation on network TypeError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(request('/x', { method: 'POST', body: '{}' })).rejects.toThrow(OfflineError)
    expect(enqueue).toHaveBeenCalledWith('POST', '/x', '{}', undefined)
  })

  it('by default enqueues mutation on AbortError (timeout treated as offline)', async () => {
    fetchMock.mockRejectedValue(new DOMException('The operation was aborted', 'AbortError'))

    await expect(request('/x', { method: 'POST', body: '{}' })).rejects.toThrow(OfflineError)
    expect(enqueue).toHaveBeenCalledTimes(1)
  })

  it('with _offlineEnqueue:false — AbortError is NOT enqueued and propagates', async () => {
    const abort = new DOMException('The operation was aborted', 'AbortError')
    fetchMock.mockRejectedValue(abort)

    await expect(
      request('/x', { method: 'POST', body: '{}', _offlineEnqueue: false }),
    ).rejects.toBe(abort)
    expect(enqueue).not.toHaveBeenCalled()
  })

  it('with _offlineEnqueue:false — TypeError (network) is NOT enqueued and propagates', async () => {
    const err = new TypeError('Failed to fetch')
    fetchMock.mockRejectedValue(err)

    await expect(
      request('/x', { method: 'POST', body: '{}', _offlineEnqueue: false }),
    ).rejects.toThrow(err)
    expect(enqueue).not.toHaveBeenCalled()
  })

  it('with _offlineEnqueue:false — offline navigator does not pre-enqueue', async () => {
    setOnline(false)
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(
      request('/x', { method: 'POST', body: '{}', _offlineEnqueue: false }),
    ).rejects.toThrow(TypeError)
    expect(enqueue).not.toHaveBeenCalled()
  })

  it('with _offlineEnqueue:false — 5xx ApiError propagates with detail, not queued', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Прокси Telegram не отвечает' }), {
        status: 503,
        statusText: 'Service Unavailable',
      }),
    )

    const promise = request('/channels/telegram/connect', {
      method: 'POST',
      body: '{}',
      _offlineEnqueue: false,
    })
    await expect(promise).rejects.toMatchObject({ status: 503 })
    await expect(promise).rejects.toBeInstanceOf(ApiError)
    expect(enqueue).not.toHaveBeenCalled()
  })
})

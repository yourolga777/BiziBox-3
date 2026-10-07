import { beforeEach, describe, expect, it, vi } from 'vitest'
import { openDB } from 'idb'
import { QueryClient } from '@tanstack/react-query'
import { processQueue, SYNC_COMPLETE } from '../sync'
import { enqueue } from '../queue'
import { getMessagesFromCache, getPendingCount, getPendingMutations, getPausedMutations, addMutation } from '../db'
import { registerQueryClient } from '../queryClient'

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, request: vi.fn(), isOfflineError: vi.fn() }
})

import { request, isOfflineError, ApiError } from '../../api/client'

function setOnline(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true })
}

async function clearStores(): Promise<void> {
  const db = await openDB('bizibox-offline')
  for (const store of ['mutations', 'messages', 'contacts', 'tasks']) {
    if (db.objectStoreNames.contains(store)) await db.clear(store)
  }
  db.close()
}

beforeEach(async () => {
  setOnline(true)
  vi.mocked(request).mockReset()
  vi.mocked(isOfflineError).mockReset()
  registerQueryClient(new QueryClient())
  await clearStores()
})

describe('processQueue', () => {
  it('AC5: syncs a pending mutation on success, removes it and invalidates queries', async () => {
    const qc = new QueryClient()
    registerQueryClient(qc)
    const invalidate = vi.spyOn(qc, 'invalidateQueries')
    vi.mocked(request).mockResolvedValue({ ok: true })
    await enqueue('POST', '/messages/send', '{}', -1)

    const complete = vi.fn()
    window.addEventListener(SYNC_COMPLETE, complete)

    const result = await processQueue()

    expect(result).toEqual({ synced: 1, failed: 0, total: 1 })
    expect(request).toHaveBeenCalledWith('/messages/send', {
      method: 'POST',
      body: '{}',
      _skipEnqueue: true,
    })
    expect(await getPendingCount()).toBe(0)
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['messages'] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['dialog'] })
    expect(complete).toHaveBeenCalledTimes(1)
    expect(complete.mock.calls[0][0].detail).toEqual({ synced: 1, failed: 0, total: 1 })

    window.removeEventListener(SYNC_COMPLETE, complete)
  })

  it('AC6: network error — mutation stays pending, nothing counted as failed', async () => {
    vi.mocked(request).mockRejectedValue(new TypeError('Failed to fetch'))
    vi.mocked(isOfflineError).mockReturnValue(true)
    await enqueue('POST', '/messages/send', '{}', -2)

    const result = await processQueue()

    expect(result).toEqual({ synced: 0, failed: 0, total: 1 })
    const pending = await getPendingMutations()
    expect(pending).toHaveLength(1)
    expect(pending[0].status).toBe('pending')
  })

  it('AC7: non-offline error — mutation marked failed with error message', async () => {
    vi.mocked(request).mockRejectedValue(new Error('Unknown error'))
    vi.mocked(isOfflineError).mockReturnValue(false)
    await enqueue('POST', '/messages/send', '{}', -3)

    const result = await processQueue()

    expect(result).toEqual({ synced: 0, failed: 1, total: 1 })
    expect(await getPendingCount()).toBe(0)
    const retryable = await getPendingMutations()
    expect(retryable).toHaveLength(1)
    expect(retryable[0].status).toBe('failed')
    const db = await openDB('bizibox-offline')
    const all = await db.getAll('mutations')
    db.close()
    expect(all).toHaveLength(1)
    expect(all[0]).toMatchObject({ status: 'failed', error: 'Unknown error' })
  })

  it('AC8: offline — nothing is sent, mutation stays pending', async () => {
    setOnline(false)
    await enqueue('POST', '/messages/send', '{}', -4)

    const result = await processQueue()

    expect(result).toEqual({ synced: 0, failed: 0, total: 1 })
    expect(request).not.toHaveBeenCalled()
    expect(await getPendingCount()).toBe(1)
  })

  it('AC9: re-entrant call while syncing returns empty result', async () => {
    vi.mocked(request).mockImplementation(() => new Promise((resolve) => setTimeout(() => resolve({ ok: true }), 50)))
    await enqueue('POST', '/messages/send', '{}', -5)
    await enqueue('POST', '/messages/send', '{}', -6)

    const first = processQueue()
    const second = processQueue()

    expect(await second).toEqual({ synced: 0, failed: 0, total: 0 })
    const firstResult = await first
    expect(firstResult.synced).toBe(2)
    expect(await getPendingCount()).toBe(0)
  })

  it('no-op when queue is empty', async () => {
    const result = await processQueue()
    expect(result).toEqual({ synced: 0, failed: 0, total: 0 })
    expect(request).not.toHaveBeenCalled()
  })

  it('stores the server message in IndexedDB cache after successful sync', async () => {
    const qc = new QueryClient()
    registerQueryClient(qc)
    const serverMessage = {
      id: 42,
      contact_id: 1,
      channel_message_id: 'tg_42',
      content: 'sent reply',
      direction: 'outgoing',
      status: 'read',
    }
    vi.mocked(request).mockResolvedValue(serverMessage)
    await enqueue('POST', '/messages/send', JSON.stringify({}), -7)

    const result = await processQueue()

    expect(result).toEqual({ synced: 1, failed: 0, total: 1 })
    const cached = await getMessagesFromCache()
    expect(cached).toHaveLength(1)
    expect(cached[0]).toMatchObject({ id: 42, direction: 'outgoing', content: 'sent reply' })
    expect(cached[0]).not.toHaveProperty('id', -7)
  })

  it('replaces the pending message in react-query cache without duplicates', async () => {
    const qc = new QueryClient()
    registerQueryClient(qc)
    const pending = { id: -7, contact_id: 1, direction: 'outgoing', content: 'sent reply', status: 'read', channel_message_id: null }
    const serverMessage = {
      id: 42,
      contact_id: 1,
      channel_message_id: 'tg_42',
      content: 'sent reply',
      direction: 'outgoing',
      status: 'read',
    }
    qc.setQueryData(['dialog', 1], [pending])
    vi.mocked(request).mockResolvedValue(serverMessage)
    await enqueue('POST', '/messages/send', '{}', -7)

    await processQueue()

    const dialog = qc.getQueryData(['dialog', 1]) as Array<Record<string, unknown>>
    expect(dialog).toHaveLength(1)
    expect(dialog[0]).toMatchObject({ id: 42 })
  })

  it('AC6: does not duplicate when the server message is already cached by channel_message_id', async () => {
    const qc = new QueryClient()
    registerQueryClient(qc)
    const serverMessage = {
      id: 42,
      contact_id: 1,
      channel_message_id: 'tg_42',
      content: 'sent reply',
      direction: 'outgoing',
      status: 'read',
    }
    qc.setQueryData(['dialog', 1], [serverMessage])
    vi.mocked(request).mockResolvedValue(serverMessage)
    await enqueue('POST', '/messages/send', '{}', -8)

    await processQueue()

    const dialog = qc.getQueryData(['dialog', 1]) as Array<Record<string, unknown>>
    expect(dialog).toHaveLength(1)
  })

  it('R1-18.1: 422 ApiError — mutation marked failed with retry_count up and future next_retry_at', async () => {
    vi.mocked(request).mockRejectedValue(new ApiError(422, 'Unprocessable Entity', 'validation error'))
    await enqueue('POST', '/messages/send', '{}', -9)

    const result = await processQueue()

    expect(result).toEqual({ synced: 0, failed: 1, total: 1 })
    const db = await openDB('bizibox-offline')
    const all = await db.getAll('mutations')
    db.close()
    expect(all).toHaveLength(1)
    expect(all[0]).toMatchObject({ status: 'failed', error: 'HTTP 422: validation error' })
    expect(all[0].retry_count).toBeGreaterThan(0)
    expect(all[0].next_retry_at).not.toBeNull()
    expect(all[0].next_retry_at as number).toBeGreaterThan(Date.now())
  })

  it('R1-18.2: 401 ApiError — mutation marked paused, others still processed', async () => {
    vi.mocked(request)
      .mockRejectedValueOnce(new ApiError(401, 'Unauthorized', 'auth required'))
      .mockResolvedValueOnce({ ok: true })
    await enqueue('POST', '/messages/send', '{}', -10)
    await enqueue('POST', '/messages/send', '{}', -11)

    const result = await processQueue()

    expect(result).toEqual({ synced: 1, failed: 1, total: 2 })
    const paused = await getPausedMutations()
    expect(paused).toHaveLength(1)
    expect(paused[0]).toMatchObject({ status: 'paused', error: 'HTTP 401: auth required' })
    expect(await getPendingCount()).toBe(0)
  })

  it('R1-18.3: 5xx ApiError — mutation stays pending and loop breaks', async () => {
    vi.mocked(request).mockRejectedValue(new ApiError(500, 'Internal Server Error', 'boom'))
    vi.mocked(isOfflineError).mockReturnValue(true)
    await enqueue('POST', '/messages/send', '{}', -12)

    const result = await processQueue()

    expect(result).toEqual({ synced: 0, failed: 0, total: 1 })
    const pending = await getPendingMutations()
    expect(pending).toHaveLength(1)
    expect(pending[0].status).toBe('pending')
  })

  it('R1-18.4: mutation with future next_retry_at is skipped, stays pending', async () => {
    await addMutation({
      method: 'POST',
      path: '/messages/send',
      body: '{}',
      status: 'pending',
      localId: -13,
      retry_count: 3,
      next_retry_at: Date.now() + 60_000,
    })

    const result = await processQueue()

    expect(result).toEqual({ synced: 0, failed: 0, total: 1 })
    expect(request).not.toHaveBeenCalled()
    const pending = await getPendingMutations()
    expect(pending).toHaveLength(1)
    expect(pending[0].status).toBe('pending')
  })

})

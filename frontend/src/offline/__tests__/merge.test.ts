import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { QueryClient } from '@tanstack/react-query'
import { mergeMessages, maxMessageId, incrementalFetch } from '../merge'

vi.mock('../db', () => ({
  getMessagesFromCache: vi.fn(),
  getMaxMessageId: vi.fn(),
}))

import { getMessagesFromCache, getMaxMessageId } from '../db'

const m = (id: number, created_at: string): { id: number; created_at: string } => ({ id, created_at })

function fakeQueryClient(): QueryClient {
  return {
    getQueryData: () => undefined,
  } as unknown as QueryClient
}

describe('maxMessageId', () => {
  it('returns max id from list', () => {
    expect(maxMessageId([m(3, 'a'), m(9, 'b'), m(1, 'c')])).toBe(9)
  })

  it('returns null for empty list', () => {
    expect(maxMessageId([])).toBeNull()
  })
})

describe('mergeMessages', () => {
  it('de-dups by id keeping fresh over base', () => {
    const base = [m(1, '2026-01-01T00:00:00Z'), m(2, '2026-01-02T00:00:00Z')]
    const fresh = [m(2, '2026-01-03T00:00:00Z'), m(3, '2026-01-04T00:00:00Z')]
    const result = mergeMessages(base, fresh)
    expect(result).toHaveLength(3)
    expect(result.map((x) => x.id)).toEqual([3, 2, 1])
    expect(result.find((x) => x.id === 2)?.created_at).toBe('2026-01-03T00:00:00Z')
  })

  it('sorts by created_at desc', () => {
    const base = [m(1, '2026-01-01T00:00:00Z'), m(2, '2026-01-03T00:00:00Z')]
    const fresh = [m(3, '2026-01-02T00:00:00Z')]
    expect(mergeMessages(base, fresh).map((x) => x.id)).toEqual([2, 3, 1])
  })

  it('caps result at MAX_MESSAGES (500)', () => {
    const base = Array.from({ length: 500 }, (_, i) => m(i, `2026-01-01T00:00:${String(i % 60).padStart(2, '0')}Z`))
    const fresh = [m(1000, '2026-01-02T00:00:00Z')]
    const result = mergeMessages(base, fresh)
    expect(result).toHaveLength(500)
    expect(result[0].id).toBe(1000)
  })
})

describe('incrementalFetch', () => {
  beforeEach(() => {
    vi.mocked(getMessagesFromCache).mockReset()
    vi.mocked(getMaxMessageId).mockReset()
  })

  it('fetches with min_id from prev data when prev exists', async () => {
    const qc = {
      getQueryData: () => [m(7, '2026-01-02T00:00:00Z'), m(5, '2026-01-01T00:00:00Z')],
    } as unknown as QueryClient
    const fetcher = vi.fn(async (minId?: number) => {
      expect(minId).toBe(7)
      return [m(8, '2026-01-03T00:00:00Z')]
    })
    const save = vi.fn()

    const result = await incrementalFetch(qc, ['messages', 'inbox'], fetcher, save)
    expect(result.map((x) => x.id)).toEqual([8, 7, 5])
    expect(save).toHaveBeenCalledWith([m(8, '2026-01-03T00:00:00Z')])
  })

  it('falls back to IndexedDB cache + max id when prev empty', async () => {
    vi.mocked(getMessagesFromCache).mockResolvedValue([m(3, '2026-01-01T00:00:00Z')])
    vi.mocked(getMaxMessageId).mockResolvedValue(3)
    const qc = fakeQueryClient()
    const fetcher = vi.fn(async (minId?: number) => {
      expect(minId).toBe(3)
      return [m(4, '2026-01-02T00:00:00Z')]
    })
    const save = vi.fn()

    const result = await incrementalFetch(qc, ['messages', 'inbox'], fetcher, save)
    expect(result.map((x) => x.id)).toEqual([4, 3])
    expect(save).toHaveBeenCalledWith([m(4, '2026-01-02T00:00:00Z')])
  })

  it('fetches full when no cache and no prev', async () => {
    vi.mocked(getMessagesFromCache).mockResolvedValue([])
    vi.mocked(getMaxMessageId).mockResolvedValue(null)
    const fetcher = vi.fn(async (minId?: number) => {
      expect(minId).toBeUndefined()
      return [m(1, '2026-01-01T00:00:00Z')]
    })
    const result = await incrementalFetch(fakeQueryClient(), ['messages', 'inbox'], fetcher, vi.fn())
    expect(result.map((x) => x.id)).toEqual([1])
  })

  it('returns base when offline and fetch fails', async () => {
    const qc = {
      getQueryData: () => [m(7, 'a')],
    } as unknown as QueryClient
    const fetcher = vi.fn(async () => {
      throw new Error('network down')
    })
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true })

    const result = await incrementalFetch(qc, ['messages', 'inbox'], fetcher, vi.fn())
    expect(result.map((x) => x.id)).toEqual([7])
  })

  it('rethrows when online and fetch fails', async () => {
    const qc = {
      getQueryData: () => [m(7, 'a')],
    } as unknown as QueryClient
    const fetcher = vi.fn(async () => {
      throw new Error('500')
    })
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })

    await expect(incrementalFetch(qc, ['messages', 'inbox'], fetcher, vi.fn())).rejects.toThrow('500')
  })

  it('does not save when fresh is empty', async () => {
    const qc = {
      getQueryData: () => [m(7, 'a')],
    } as unknown as QueryClient
    const fetcher = vi.fn(async (): Promise<{ id: number; created_at: string }[]> => [])
    const save = vi.fn()

    const result = await incrementalFetch(qc, ['messages', 'inbox'], fetcher, save)
    expect(result.map((x) => x.id)).toEqual([7])
    expect(save).not.toHaveBeenCalled()
  })
})

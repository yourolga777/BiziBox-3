import type { QueryClient } from '@tanstack/react-query'
import { isOfflineError } from '../api/client'
import { getMaxMessageId, getMessagesFromCache } from './db'

const MAX_MESSAGES = 500

export interface Mergable {
  id: number
  created_at?: string | null
}

export function maxMessageId(messages: Mergable[]): number | null {
  let max: number | null = null
  for (const m of messages) {
    if (m.id > (max ?? 0)) max = m.id
  }
  return max
}

export function mergeMessages<T extends Mergable>(base: T[], fresh: T[]): T[] {
  const byId = new Map<number, T>()
  for (const m of base) byId.set(m.id, m)
  for (const m of fresh) byId.set(m.id, m)
  return [...byId.values()]
    .sort((a, b) => {
      const ta = new Date(a.created_at ?? 0).getTime()
      const tb = new Date(b.created_at ?? 0).getTime()
      return tb - ta
    })
    .slice(0, MAX_MESSAGES)
}

export async function incrementalFetch<T extends Mergable>(
  queryClient: QueryClient,
  queryKey: readonly unknown[],
  fetcher: (minId?: number) => Promise<T[]>,
  save: (msgs: T[]) => void,
): Promise<T[]> {
  const prev = queryClient.getQueryData<T[]>(queryKey) ?? []
  let base = prev
  let minId: number | null = null

  if (prev.length === 0) {
    const cached = (await getMessagesFromCache()) as unknown as T[]
    base = cached
    minId = await getMaxMessageId()
  } else {
    minId = maxMessageId(prev)
  }

  try {
    const fresh = await fetcher(minId ?? undefined)
    if (fresh.length > 0) save(fresh)
    return mergeMessages(base, fresh)
  } catch (err) {
    if (!navigator.onLine || isOfflineError(err)) return base
    throw err
  }
}

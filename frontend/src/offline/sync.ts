import { request, isOfflineError, ApiError } from '../api/client'
import { getPendingMutations, markMutationDone, markMutationFailed, markMutationPaused, markMutationPermanentFailed, saveToStore, deleteFromStore } from './db'
import type { OfflineMutation } from './db'
import { getQueryClient } from './queryClient'
import { CACHE_MAP } from './cacheMap'

export const SYNC_COMPLETE = 'bizibox:sync-complete'

let syncing = false

interface EntityLike {
  id?: number
}

function upsertEntityInCache(localId: number, entity: EntityLike, queryKeys: string[]): void {
  const qc = getQueryClient()
  if (!qc) return
  for (const query of qc.getQueryCache().getAll()) {
    const data = query.state.data
    if (!Array.isArray(data)) continue

    const qk = query.queryKey[0] as string
    if (!queryKeys.includes(qk)) continue

    const items = data as Array<{ id?: number }>
    const withoutFake = items.filter(item => item.id !== localId)
    const hasDup = withoutFake.some(item => item.id === entity.id)

    if (!hasDup) {
      qc.setQueryData(query.queryKey, [entity, ...withoutFake])
    } else {
      qc.setQueryData(query.queryKey, withoutFake.map(item => item.id === entity.id ? entity : item))
    }
  }
}

function removeEntityFromCache(entityId: number, queryKeys: string[]): void {
  const qc = getQueryClient()
  if (!qc) return
  for (const query of qc.getQueryCache().getAll()) {
    const data = query.state.data
    if (!Array.isArray(data)) continue

    const qk = query.queryKey[0] as string
    if (!queryKeys.includes(qk)) continue

    const items = data as Array<{ id?: number }>
    qc.setQueryData(query.queryKey, items.filter(item => item.id !== entityId))
  }
}

function storeFromSegment(path: string): { store: string; queryKeys: string[] } | undefined {
  const segment = path.split('/')[1]
  switch (segment) {
    case 'contacts': return { store: 'contacts', queryKeys: ['contacts', 'contact', 'notes', 'timeline'] }
    case 'tasks': return { store: 'tasks', queryKeys: ['tasks', 'task'] }
    case 'messages': return { store: 'messages', queryKeys: ['messages', 'dialog', 'inbox', 'feed', 'archive', 'spam'] }
    default: return undefined
  }
}

const ALL_ENTITY_KEYS = {
  messages: ['messages', 'dialog', 'inbox', 'feed', 'archive', 'spam'],
  contacts: ['contacts', 'contact', 'notes', 'timeline'],
  tasks: ['tasks', 'task'],
  folders: ['folders'],
  tags: ['tags'],
}

export function invalidateAllEntityCaches(): void {
  const qc = getQueryClient()
  if (!qc) return
  for (const keys of Object.values(ALL_ENTITY_KEYS)) {
    for (const key of keys) {
      qc.invalidateQueries({ queryKey: [key] })
    }
  }
}

function isPermanentError(status: number): boolean {
  return status >= 400 && status < 500 && status !== 429
}

export interface SyncResult {
  synced: number
  failed: number
  total: number
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function buildFormData(mutation: OfflineMutation): FormData | null {
  const files = mutation.files
  if (!files || files.length === 0) return null
  const fd = new FormData()
  for (const [key, value] of Object.entries(mutation.formFields || {})) {
    fd.append(key, value)
  }
  for (const f of files) {
    const blob = new Blob([f.data], { type: f.mimeType })
    fd.append('files', blob, f.fileName)
  }
  return fd
}

export async function processQueue(): Promise<SyncResult> {
  if (syncing) return { synced: 0, failed: 0, total: 0 }
  syncing = true

  let synced = 0
  let failed = 0

  try {
    const mutations = await getPendingMutations()
    const total = mutations.length

    if (total === 0) {
      syncing = false
      return { synced: 0, failed: 0, total: 0 }
    }

    for (const mutation of mutations) {
      if (!navigator.onLine) break

      if (mutation.next_retry_at && Date.now() < mutation.next_retry_at) continue

      try {
        const formData = buildFormData(mutation)
        const response = await request(mutation.path, {
          method: mutation.method,
          body: formData ?? mutation.body ?? undefined,
          _skipEnqueue: true,
        })

        const cacheInfo = CACHE_MAP[mutation.path] || storeFromSegment(mutation.path)

        await markMutationDone(mutation.id!, mutation.localId, cacheInfo?.store)

        if (mutation.method === 'DELETE' && mutation.entityId !== undefined) {
          if (cacheInfo?.store) {
            await deleteFromStore(cacheInfo.store, mutation.entityId)
          }
          if (cacheInfo?.queryKeys) {
            removeEntityFromCache(mutation.entityId, cacheInfo.queryKeys)
          }
        } else if (cacheInfo && mutation.localId !== undefined) {
          await saveToStore(cacheInfo.store, response)

          if (response && typeof response === 'object' && 'id' in response) {
            upsertEntityInCache(mutation.localId, response as EntityLike, cacheInfo.queryKeys)
          }
        }

        synced++
      } catch (err) {
        if (isOfflineError(err)) {
          break
        }

        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          await markMutationPaused(
            mutation.id!,
            `HTTP ${err.status}: ${err.message}`,
          )
          failed++
          continue
        }

        if (err instanceof ApiError && (err.status === 422 || err.status === 429)) {
          await markMutationFailed(
            mutation.id!,
            `HTTP ${err.status}: ${err.message}`,
          )
        } else if (err instanceof ApiError && isPermanentError(err.status)) {
          await markMutationPermanentFailed(
            mutation.id!,
            `HTTP ${err.status}: ${err.message}`,
          )
        } else {
          await markMutationFailed(
            mutation.id!,
            err instanceof Error ? err.message : String(err),
          )
        }
        failed++
      }

      if (synced + failed < total && navigator.onLine) {
        await delay(1000)
      }
    }

    const result: SyncResult = { synced, failed, total }
    window.dispatchEvent(new CustomEvent(SYNC_COMPLETE, { detail: result }))
    if (synced > 0) {
      invalidateAllEntityCaches()
    }
    return result
  } finally {
    syncing = false
  }
}

export function initSync() {
  window.addEventListener('online', () => {
    processQueue()
    invalidateAllEntityCaches()
  })
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      processQueue()
    }
  })
}

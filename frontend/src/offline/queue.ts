import { addMutation, getPendingCount, getPendingOnly, getFailedMutations, getPausedMutations, retryFailedMutation, discardFailedMutation, clearFailedMutations, resetMutationsForRetry, clearMutations, discardMutation, updateMutationBody, updateMessageContentInCache, deleteMessageFromCache, addFileMutation } from './db'
import type { OfflineMutation, PersistedFile } from './db'

export const MUTATIONS_UPDATED = 'bizibox:mutations-updated'

export async function enqueue(method: string, path: string, body?: string, localId?: number, entityId?: number): Promise<void> {
  await addMutation({
    method,
    path,
    body: body ?? null,
    status: 'pending',
    localId,
    entityId,
    retry_count: 0,
    next_retry_at: null,
  })
  window.dispatchEvent(new CustomEvent(MUTATIONS_UPDATED))
}

export async function enqueueFile(
  method: string,
  path: string,
  formFields: Record<string, string>,
  files: PersistedFile[],
  localId?: number,
): Promise<void> {
  await addFileMutation({ method, path, formFields, files, localId })
  window.dispatchEvent(new CustomEvent(MUTATIONS_UPDATED))
}

export async function getCount(): Promise<number> {
  return getPendingCount()
}

export async function getFailed(): Promise<OfflineMutation[]> {
  return getFailedMutations()
}

export async function getPaused(): Promise<OfflineMutation[]> {
  return getPausedMutations()
}

export async function getPending(): Promise<OfflineMutation[]> {
  return getPendingOnly()
}

export async function retryFailed(id: number): Promise<void> {
  await retryFailedMutation(id)
  window.dispatchEvent(new CustomEvent(MUTATIONS_UPDATED))
}

export async function discardFailed(id: number): Promise<void> {
  await discardFailedMutation(id)
  window.dispatchEvent(new CustomEvent(MUTATIONS_UPDATED))
}

export async function discardPending(id: number, localId?: number): Promise<void> {
  await discardMutation(id)
  if (localId !== undefined) {
    await deleteMessageFromCache(localId)
  }
  window.dispatchEvent(new CustomEvent(MUTATIONS_UPDATED))
}

export async function editPendingMessage(id: number, body: string, localId?: number, content?: string): Promise<void> {
  await updateMutationBody(id, body)
  if (localId !== undefined && content !== undefined) {
    await updateMessageContentInCache(localId, content)
  }
  window.dispatchEvent(new CustomEvent(MUTATIONS_UPDATED))
}

export { clearFailedMutations, resetMutationsForRetry, clearMutations }

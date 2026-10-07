import { beforeEach, describe, expect, it, vi } from 'vitest'
import { openDB } from 'idb'
import { enqueue, discardPending, editPendingMessage } from '../queue'
import { getPendingCount, getPendingMutations, getMessageFromCache, saveMessages } from '../db'

async function clearStores(): Promise<void> {
  const db = await openDB('bizibox-offline')
  for (const store of ['mutations', 'messages', 'contacts', 'orders', 'tasks']) {
    if (db.objectStoreNames.contains(store)) await db.clear(store)
  }
  db.close()
}

beforeEach(async () => {
  await clearStores()
})

describe('enqueue', () => {
  it('AC4: adds a pending mutation to IndexedDB and dispatches MUTATIONS_UPDATED', async () => {
    const handler = vi.fn()
    window.addEventListener('bizibox:mutations-updated', handler)

    await enqueue('POST', '/messages/send', '{"content":"hi"}', -7)

    expect(await getPendingCount()).toBe(1)
    const mutations = await getPendingMutations()
    expect(mutations).toHaveLength(1)
    expect(mutations[0]).toMatchObject({
      method: 'POST',
      path: '/messages/send',
      body: '{"content":"hi"}',
      status: 'pending',
      localId: -7,
    })
    expect(handler).toHaveBeenCalledTimes(1)

    window.removeEventListener('bizibox:mutations-updated', handler)
  })

  it('queues multiple mutations in order', async () => {
    await enqueue('POST', '/a', '1')
    await enqueue('PATCH', '/b', '2')

    const mutations = await getPendingMutations()
    expect(mutations.map((m) => m.path)).toEqual(['/a', '/b'])
  })
})

describe('discardPending', () => {
  it('удаляет ожидающую запись и локальное сообщение из кеша', async () => {
    await enqueue('POST', '/messages/send', '{"content":"hi"}', -7)
    await saveMessages([{ id: -7, content: 'hi', sync_pending: true }])

    const [m] = await getPendingMutations()
    await discardPending(m.id!, -7)

    expect(await getPendingCount()).toBe(0)
    expect(await getMessageFromCache(-7)).toBeUndefined()
  })
})

describe('editPendingMessage', () => {
  it('обновляет тело мутации и текст локального сообщения', async () => {
    await enqueue('POST', '/messages/send', '{"message_id":1,"content":"hi"}', -7)
    await saveMessages([{ id: -7, content: 'hi', sync_pending: true }])

    const [m] = await getPendingMutations()
    await editPendingMessage(m.id!, '{"message_id":1,"content":"bye"}', -7, 'bye')

    const [updated] = await getPendingMutations()
    expect(JSON.parse(updated.body!)).toMatchObject({ message_id: 1, content: 'bye' })
    expect((await getMessageFromCache(-7))).toMatchObject({ content: 'bye' })
  })
})

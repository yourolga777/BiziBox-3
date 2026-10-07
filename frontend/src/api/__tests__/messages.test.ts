import { beforeEach, describe, expect, it, vi } from 'vitest'
import { openDB } from 'idb'
import { sendReply } from '../messages'
import { getMessagesFromCache, getPendingCount, getPendingMutations } from '../../offline/db'

vi.mock('../client', () => ({
  request: vi.fn(),
  isOfflineError: vi.fn(),
}))

import { request, isOfflineError } from '../client'

const DATA = { message_id: 42, content: 'Привет!' }

function setOnline(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', { value, configurable: true })
}

async function clearStores(): Promise<void> {
  const db = await openDB('bizibox-offline')
  for (const store of ['mutations', 'messages', 'contacts', 'orders', 'tasks']) {
    if (db.objectStoreNames.contains(store)) await db.clear(store)
  }
  db.close()
}

beforeEach(async () => {
  setOnline(true)
  vi.mocked(request).mockReset()
  vi.mocked(isOfflineError).mockReset()
  await clearStores()
})

describe('sendReply', () => {
  it('AC1: offline — returns pending message and enqueues mutation', async () => {
    setOnline(false)

    const msg = await sendReply(DATA, 5)

    expect(msg.id).toBeLessThan(0)
    expect(msg.channel).toBe('pending')
    expect(msg.sync_pending).toBe(true)
    expect(msg.direction).toBe('outgoing')
    expect(msg.status).toBe('read')
    expect(msg.content).toBe('Привет!')
    expect(msg.contact_id).toBe(5)
    expect(request).not.toHaveBeenCalled()

    const mutations = await getPendingMutations()
    expect(mutations).toHaveLength(1)
    expect(mutations[0]).toMatchObject({
      method: 'POST',
      path: '/messages/send',
      status: 'pending',
      localId: msg.id,
    })
    expect(mutations[0].body).not.toBeNull()
    const parsed = JSON.parse(mutations[0].body!)
    expect(parsed).toMatchObject({ message_id: 42, content: 'Привет!' })
    expect(typeof parsed.client_request_id).toBe('string')
    expect(parsed.client_request_id.length).toBeGreaterThan(0)

    const cached = await getMessagesFromCache()
    expect(cached.some((m) => (m as { id: number }).id === msg.id)).toBe(true)
  })

  it('AC2: online + 5xx — falls back to pending (isOfflineError)', async () => {
    setOnline(true)
    vi.mocked(request).mockRejectedValue({ status: 500 })
    vi.mocked(isOfflineError).mockReturnValue(true)

    const msg = await sendReply(DATA, 7)

    expect(msg.id).toBeLessThan(0)
    expect(msg.sync_pending).toBe(true)
    expect(await getPendingCount()).toBe(1)
  })

  it('AC3: online success — uses _skipEnqueue, no mutation queued', async () => {
    setOnline(true)
    const serverMessage = { id: 100, content: 'Привет!', channel: 'telegram' }
    vi.mocked(request).mockResolvedValue(serverMessage)

    const msg = await sendReply(DATA, 5)

    expect(msg.id).toBe(100)
    expect(request).toHaveBeenCalledWith('/messages/send', expect.objectContaining({
      method: 'POST',
      _skipEnqueue: true,
    }))
    const callBody = (request as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as string
    const parsed = JSON.parse(callBody)
    expect(parsed).toMatchObject({ message_id: 42, content: 'Привет!' })
    expect(typeof parsed.client_request_id).toBe('string')
    expect(await getPendingCount()).toBe(0)
    expect(isOfflineError).not.toHaveBeenCalled()
  })
})

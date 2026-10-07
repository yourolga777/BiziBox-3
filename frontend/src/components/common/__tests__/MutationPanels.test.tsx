import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { openDB } from 'idb'
import FailedMutationsPanel from '../FailedMutationsPanel'
import PendingMutationsPanel from '../PendingMutationsPanel'
import { enqueue } from '../../../offline/queue'
import { markMutationFailed, markMutationPaused, markMutationPermanentFailed, getPendingMutations, getFailedMutations, saveMessages } from '../../../offline/db'

vi.mock('../../../offline/sync', () => ({
  processQueue: vi.fn().mockResolvedValue({ synced: 0, failed: 0, total: 0 }),
  invalidateAllEntityCaches: vi.fn(),
}))

import { processQueue } from '../../../offline/sync'
const mockProcessQueue = vi.mocked(processQueue)

async function clearStores(): Promise<void> {
  const db = await openDB('bizibox-offline')
  for (const store of ['mutations', 'messages', 'contacts', 'orders', 'tasks']) {
    if (db.objectStoreNames.contains(store)) await db.clear(store)
  }
  db.close()
}

beforeEach(async () => {
  await clearStores()
  vi.clearAllMocks()
})

describe('FailedMutationsPanel', () => {
  it('renders failed and paused mutations with copy button', async () => {
    await enqueue('POST', '/messages/send', '{"text":"hello"}', -1)
    await enqueue('POST', '/tasks', '{"title":"x"}', -2)
    const db = await openDB('bizibox-offline')
    const all = await db.getAll('mutations')
    await markMutationFailed(all[0].id!, 'Network error')
    await markMutationPaused(all[1].id!, 'Conflict')
    db.close()

    const onClose = vi.fn()
    render(<FailedMutationsPanel onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Не синхронизировано: 2')).toBeInTheDocument()
    })

    expect(screen.getByText('/messages/send')).toBeInTheDocument()
    expect(screen.getByText('/tasks')).toBeInTheDocument()
    expect(screen.getByText('Network error')).toBeInTheDocument()
    expect(screen.getByText('Conflict')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Копировать/i })).toBeInTheDocument()
  })

  it('does not close when selecting text inside panel', async () => {
    await enqueue('POST', '/messages/send', '{"text":"hello"}', -1)
    const db = await openDB('bizibox-offline')
    const all = await db.getAll('mutations')
    await markMutationFailed(all[0].id!, 'Err')
    db.close()

    const onClose = vi.fn()
    const { container } = render(<FailedMutationsPanel onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('/messages/send')).toBeInTheDocument()
    })

    const overlay = container.querySelector('[role="dialog"]') as HTMLElement
    // Simulate text selection: mousedown on content, mouseup on overlay
    const content = screen.getByText('/messages/send')
    fireEvent.mouseDown(content)
    fireEvent.mouseUp(overlay)
    expect(onClose).not.toHaveBeenCalled()

    // Direct click on overlay closes
    fireEvent.mouseDown(overlay)
    fireEvent.mouseUp(overlay)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('retry all resets permanent failures to pending and runs processQueue', async () => {
    await enqueue('POST', '/channels/email/download', undefined, -3)
    const db = await openDB('bizibox-offline')
    const all = await db.getAll('mutations')
    await markMutationPermanentFailed(all[0].id!, 'Channel email not found')
    db.close()

    expect((await getFailedMutations())[0].retry_count).toBe(999)

    const onClose = vi.fn()
    render(<FailedMutationsPanel onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Не синхронизировано: 1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Повторить всё/i }))

    await waitFor(() => {
      expect(mockProcessQueue).toHaveBeenCalled()
    })

    const pending = await getPendingMutations()
    expect(pending).toHaveLength(1)
    expect(pending[0]).toMatchObject({ status: 'pending', retry_count: 0, error: undefined })
  })

  it('clear all removes failed and paused mutations', async () => {
    await enqueue('POST', '/messages/send', '{}', -4)
    await enqueue('POST', '/tasks', '{}', -5)
    const db = await openDB('bizibox-offline')
    const all = await db.getAll('mutations')
    await markMutationPermanentFailed(all[0].id!, 'HTTP 404: gone')
    await markMutationPaused(all[1].id!, 'HTTP 401: auth')
    db.close()

    const onClose = vi.fn()
    render(<FailedMutationsPanel onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Не синхронизировано: 2')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Очистить всё/i }))

    await waitFor(() => {
      expect(screen.getByText('Нет ошибок синхронизации')).toBeInTheDocument()
    })
  })
})

describe('PendingMutationsPanel', () => {
  it('renders pending mutations', async () => {
    await enqueue('POST', '/messages/send', '{"text":"hello"}', -1)
    await enqueue('PATCH', '/orders/5', '{"status":"done"}', -2)

    const onClose = vi.fn()
    render(<PendingMutationsPanel onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Ожидает отправки: 2')).toBeInTheDocument()
    })

    expect(screen.getByText('/messages/send')).toBeInTheDocument()
    expect(screen.getByText('/orders/5')).toBeInTheDocument()
    expect(screen.getByText(/hello/)).toBeInTheDocument()
  })

  it('отменяет ожидающее сообщение из панели', async () => {
    await enqueue('POST', '/messages/send', '{"message_id":1,"content":"hello"}', -1)
    await saveMessages([{ id: -1, content: 'hello', sync_pending: true }])

    const onClose = vi.fn()
    render(<PendingMutationsPanel onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Ожидает отправки: 1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Отменить/i }))

    await waitFor(() => {
      expect(screen.getByText('Нет ожидающих отправки данных')).toBeInTheDocument()
    })

    expect(await getPendingMutations()).toHaveLength(0)
  })

  it('изменяет текст ожидающего сообщения', async () => {
    await enqueue('POST', '/messages/send', '{"message_id":1,"content":"hello"}', -1)

    const onClose = vi.fn()
    render(<PendingMutationsPanel onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByText('Ожидает отправки: 1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Изменить/i }))

    const textarea = await screen.findByLabelText('Текст ожидающего сообщения')
    fireEvent.change(textarea, { target: { value: 'edited text' } })
    fireEvent.click(screen.getByRole('button', { name: /Сохранить/i }))

    await waitFor(() => {
      expect(screen.getByText(/edited text/)).toBeInTheDocument()
    })

    const [m] = await getPendingMutations()
    expect(JSON.parse(m.body!)).toMatchObject({ message_id: 1, content: 'edited text' })
  })
})

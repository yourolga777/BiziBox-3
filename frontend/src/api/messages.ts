import type { SendMessageRequest, SendReplyRequest } from '../types/channel'
import type { Message, MessageCreate, MessageUpdate } from '../types/message'
import type { Thread } from '../types/inbox'
import { saveMessages } from '../offline/db'
import { enqueue, enqueueFile } from '../offline/queue'
import { request, isOfflineError } from './client'

const API_BASE = '/api'

export function getAttachmentDownloadUrl(
  messageId: number,
  attachmentId: number,
): string {
  return `${API_BASE}/messages/${messageId}/attachments/${attachmentId}/download`
}

export const messageApi = {
  getAll: (params?: { contact_id?: number; channel?: string; unread?: boolean; skip?: number; limit?: number; min_id?: number }) => {
    const search = new URLSearchParams()
    if (params?.contact_id) search.set('contact_id', String(params.contact_id))
    if (params?.channel) search.set('channel', params.channel)
    if (params?.unread) search.set('unread', 'true')
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    if (params?.min_id) search.set('min_id', String(params.min_id))
    const qs = search.toString()
    return request<Message[]>(`/messages${qs ? `?${qs}` : ''}`)
  },

  getById: (id: number) => request<Message>(`/messages/${id}`),

  create: (data: MessageCreate) =>
    request<Message>('/messages/', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: number, data: MessageUpdate) =>
    request<Message>(`/messages/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  snooze: (id: number, until: string) =>
    request<Message>(`/messages/${id}/snooze`, { method: 'PATCH', body: JSON.stringify({ until }), _entityId: id }),

  delete: (id: number) =>
    request<void>(`/messages/${id}`, { method: 'DELETE', _entityId: id }),

  deleteContact: (contactId: number) =>
    request<{ deleted: number }>(`/messages/contact/${contactId}`, { method: 'DELETE', _entityId: contactId }),

  markContactUnread: (contactId: number) =>
    request<{ updated: number }>(`/messages/contact/${contactId}/mark-unread`, { method: 'POST' }),

  markContactRead: (contactId: number) =>
    request<{ updated: number }>(`/messages/contact/${contactId}/mark-read`, { method: 'POST' }),

  bulkStatusUpdate: (ids: number[], status: string) =>
    request<{ updated: number }>('/messages/bulk/status', {
      method: 'PATCH',
      body: JSON.stringify({ ids, status }),
    }),

  bulkDelete: (ids: number[]) =>
    request<{ deleted: number }>('/messages/bulk', {
      method: 'DELETE',
      body: JSON.stringify({ ids }),
    }),

  bulkRestore: (ids: number[]) =>
    request<{ restored: number }>('/messages/bulk/restore', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),

  getDialog: (contactId: number, limit?: number, before?: { createdAt: string | null; id: number }) => {
    const params = new URLSearchParams()
    if (limit) params.set('limit', String(limit))
    if (before) {
      if (before.createdAt) params.set('before_created_at', before.createdAt)
      params.set('before_id', String(before.id))
    }
    const qs = params.toString()
    return request<Message[]>(`/messages/dialog/${contactId}${qs ? `?${qs}` : ''}`)
  },

  syncDialog: (contactId: number) =>
    request<{ new_messages: number }>(`/messages/sync-dialog/${contactId}`, { method: 'POST' }),

  generateDraft: (id: number) =>
    request<Message>(`/messages/${id}/generate-draft`, { method: 'POST' }),

  getInbox: (params?: { skip?: number; limit?: number; min_id?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    if (params?.min_id) search.set('min_id', String(params.min_id))
    const qs = search.toString()
    return request<Message[]>(`/messages/inbox${qs ? `?${qs}` : ''}`)
  },

  getThreads: (params?: { skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Thread[]>(`/messages/threads${qs ? `?${qs}` : ''}`)
  },

  getArchived: (params?: { skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Message[]>(`/messages/archive${qs ? `?${qs}` : ''}`)
  },

  getSpam: (params?: { skip?: number; limit?: number; min_id?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    if (params?.min_id) search.set('min_id', String(params.min_id))
    const qs = search.toString()
    return request<Message[]>(`/messages/spam${qs ? `?${qs}` : ''}`)
  },

  getSpamCount: () =>
    request<{ count: number }>('/messages/spam/count'),

  loadSpam: () =>
    request<{ loaded: number; messages: Message[] }>('/messages/spam/load', { method: 'POST' }),

  loadChannels: (folderId?: number) => {
    const qs = folderId ? `?folder_id=${folderId}` : ''
    return request<{ loaded: number; messages: Message[] }>(`/messages/channels/load${qs}`, { method: 'POST' })
  },

  search: (q: string, limit?: number) => {
    const params = new URLSearchParams()
    params.set('q', q)
    if (limit) params.set('limit', String(limit))
    return request<Message[]>(`/messages/search?${params.toString()}`)
  },

  loadPrevious: (contactId: number, count: number = 10) =>
    request<Message[]>('/messages/load-previous', {
      method: 'POST',
      body: JSON.stringify({ contact_id: contactId, count }),
    }),
}

let pendingSeq = 0

function newClientRequestId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

async function createPendingReply(data: SendReplyRequest, contactId: number, body: string): Promise<Message> {
  const localId = -(Date.now() + pendingSeq++)
  const now = new Date().toISOString()
  const pending: Message = {
    id: localId,
    contact_id: contactId,
    channel: 'pending',
    channel_message_id: null,
    content: data.content,
    direction: 'outgoing',
    status: 'read',
    created_at: now,
    updated_at: now,
    sync_pending: true,
  }
  await saveMessages([pending])
  await enqueue('POST', '/messages/send', body, localId)
  return pending
}

export async function sendReply(data: SendReplyRequest, contactId: number): Promise<Message> {  const clientRequestId = newClientRequestId()
  const payload: SendReplyRequest & { client_request_id?: string } = {
    ...data,
    client_request_id: clientRequestId,
  }
  const body = JSON.stringify(payload)

  if (!navigator.onLine) {
    return createPendingReply(data, contactId, body)
  }

  try {
    return await request<Message>('/messages/send', {
      method: 'POST',
      body,
      _skipEnqueue: true,
    })
  } catch (err) {
    if (isOfflineError(err)) {
      return createPendingReply(data, contactId, body)
    }
    throw err
  }
}

export async function sendFileReply(
  messageId: number,
  content: string,
  files: File[],
  contactId: number,
  recipient?: string | null,
): Promise<Message> {
  const clientRequestId = newClientRequestId()
  const formFields = {
    message_id: String(messageId),
    content,
    client_request_id: clientRequestId,
    ...(recipient ? { recipient } : {}),
  }

  const createPending = async (): Promise<Message> => {
    const localId = -(Date.now() + pendingSeq++)
    const now = new Date().toISOString()
    const pending: Message = {
      id: localId,
      contact_id: contactId,
      channel: 'pending',
      channel_message_id: null,
      content,
      direction: 'outgoing',
      status: 'read',
      created_at: now,
      updated_at: now,
      sync_pending: true,
    }
    await saveMessages([pending])
    const persisted = await Promise.all(
      files.map(async (f) => ({
        fileName: f.name,
        mimeType: f.type || 'application/octet-stream',
        data: await f.arrayBuffer(),
      })),
    )
    await enqueueFile(
      'POST',
      '/messages/send-file',
      formFields,
      persisted,
      localId,
    )
    return pending
  }

  if (!navigator.onLine) {
    return createPending()
  }

  try {
    const formData = new FormData()
    for (const [k, v] of Object.entries(formFields)) formData.append(k, v)
    for (const f of files) formData.append('files', f)
    return await request<Message>('/messages/send-file', {
      method: 'POST',
      body: formData,
      _skipEnqueue: true,
    })
  } catch (err) {
    if (isOfflineError(err)) {
      return createPending()
    }
    throw err
  }
}

export interface SendNewRequest {
  channel: string
  recipient: string
  content: string
}

async function createPendingMessage(data: SendMessageRequest, body: string): Promise<Message> {
  const localId = -(Date.now() + pendingSeq++)
  const now = new Date().toISOString()
  const pending: Message = {
    id: localId,
    contact_id: data.contact_id,
    channel: data.channel,
    channel_message_id: null,
    content: data.content,
    direction: 'outgoing',
    status: 'read',
    created_at: now,
    updated_at: now,
    sync_pending: true,
  }
  await saveMessages([pending])
  await enqueue('POST', '/messages/send-message', body, localId)
  return pending
}

export async function sendMessage(data: SendMessageRequest): Promise<Message> {
  const clientRequestId = newClientRequestId()
  const payload = { ...data, client_request_id: clientRequestId }
  const body = JSON.stringify(payload)

  if (!navigator.onLine) {
    return createPendingMessage(data, body)
  }

  try {
    return await request<Message>('/messages/send-message', {
      method: 'POST',
      body,
      _skipEnqueue: true,
    })
  } catch (err) {
    if (isOfflineError(err)) {
      return createPendingMessage(data, body)
    }
    throw err
  }
}

export async function sendFileMessage(
  contactId: number,
  channel: string,
  content: string,
  files: File[],
  recipient?: string | null,
): Promise<Message> {
  const clientRequestId = newClientRequestId()
  const formFields = {
    contact_id: String(contactId),
    channel,
    content,
    client_request_id: clientRequestId,
    ...(recipient ? { recipient } : {}),
  }

  const createPending = async (): Promise<Message> => {
    const localId = -(Date.now() + pendingSeq++)
    const now = new Date().toISOString()
    const pending: Message = {
      id: localId,
      contact_id: contactId,
      channel,
      channel_message_id: null,
      content,
      direction: 'outgoing',
      status: 'read',
      created_at: now,
      updated_at: now,
      sync_pending: true,
    }
    await saveMessages([pending])
    const persisted = await Promise.all(
      files.map(async (f) => ({
        fileName: f.name,
        mimeType: f.type || 'application/octet-stream',
        data: await f.arrayBuffer(),
      })),
    )
    await enqueueFile(
      'POST',
      '/messages/send-file-message',
      formFields,
      persisted,
      localId,
    )
    return pending
  }

  if (!navigator.onLine) {
    return createPending()
  }

  try {
    const formData = new FormData()
    for (const [k, v] of Object.entries(formFields)) formData.append(k, v)
    for (const f of files) formData.append('files', f)
    return await request<Message>('/messages/send-file-message', {
      method: 'POST',
      body: formData,
      _skipEnqueue: true,
    })
  } catch (err) {
    if (isOfflineError(err)) {
      return createPending()
    }
    throw err
  }
}

export async function sendNew(data: SendNewRequest): Promise<Message> {
  const clientRequestId = newClientRequestId()
  const payload = { ...data, client_request_id: clientRequestId }
  return request<Message>('/messages/send-new', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export interface ForwardRequest {
  message_id: number
  target_contact_id: number
  content: string
}

export async function forwardMessage(data: ForwardRequest): Promise<Message> {
  return request<Message>('/messages/forward', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
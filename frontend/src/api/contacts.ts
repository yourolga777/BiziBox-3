import type { Contact, ContactCreate, ContactUpdate, ContactsQueryParams, ContactFolder, ContactFolderCreate, ContactFolderUpdate, BulkUpdateRequest, DuplicateGroup, TimelineEvent, ContactNote, ContactNoteCreate, ImportResult, ContactTypeTemplate, ContactTypeTemplateCreate, ContactTypeTemplateUpdate } from '../types/contact'
import { request } from './client'

export const contactApi = {
  getAll: (params?: ContactsQueryParams) => {
    const search = new URLSearchParams()
    if (params?.search) search.set('search', params.search)
    if (params?.channel) search.set('channel', params.channel)
    if (params?.subsection) search.set('subsection', params.subsection)
    if (params?.life_sphere) search.set('life_sphere', params.life_sphere)
    if (params?.contact_type_ids?.length) search.set('contact_type_ids', params.contact_type_ids.join(','))
    if (params?.folder_id !== undefined && params.folder_id !== null) search.set('folder_id', String(params.folder_id))
    if (params?.is_favorite !== undefined) search.set('is_favorite', String(params.is_favorite))
    if (params?.unclassified) search.set('unclassified', 'true')
    if (params?.sort_by) search.set('sort_by', params.sort_by)
    if (params?.sort_order) search.set('sort_order', params.sort_order)
    if (params?.skip !== undefined) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Contact[]>(`/contacts${qs ? `?${qs}` : ''}`)
  },

  getById: (id: number) => request<Contact>(`/contacts/${id}`),

  create: (data: ContactCreate) =>
    request<Contact>('/contacts/', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: number, data: ContactUpdate) =>
    request<Contact>(`/contacts/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  delete: (id: number) =>
    request<void>(`/contacts/${id}`, { method: 'DELETE', _entityId: id }),

  search: (query: string, limit?: number) => {
    const qs = `search=${encodeURIComponent(query)}${limit ? `&limit=${limit}` : ''}`
    return request<Contact[]>(`/contacts?${qs}`)
  },

  merge: (primaryId: number, secondaryId: number) =>
    request<Contact>('/contacts/merge', {
      method: 'POST',
      body: JSON.stringify({ primary_id: primaryId, secondary_id: secondaryId }),
    }),

  getArchived: (params?: { skip?: number; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.skip) search.set('skip', String(params.skip))
    if (params?.limit) search.set('limit', String(params.limit))
    const qs = search.toString()
    return request<Contact[]>(`/contacts/archive${qs ? `?${qs}` : ''}`)
  },

  restore: (id: number) =>
    request<Contact>(`/contacts/${id}/restore`, { method: 'POST' }),

  block: (id: number) =>
    request<Contact>(`/contacts/${id}/block`, { method: 'POST', _entityId: id }),

  unblock: (id: number) =>
    request<Contact>(`/contacts/${id}/unblock`, { method: 'POST', _entityId: id }),

  setSpam: (id: number, spam: boolean) =>
    request<Contact>(`/contacts/${id}/set-spam?spam=${spam}`, { method: 'POST', _entityId: id }),

  bulkDelete: (ids: number[]) =>
    request<{ deleted: number }>('/contacts/bulk-delete', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),

  bulkRestore: (ids: number[]) =>
    request<{ restored: number }>('/contacts/bulk-restore', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),

  bulkMerge: (primaryId: number, secondaryIds: number[]) =>
    request<Contact>('/contacts/bulk-merge', {
      method: 'POST',
      body: JSON.stringify({ primary_id: primaryId, secondary_ids: secondaryIds }),
    }),

  getFolders: () =>
    request<ContactFolder[]>('/folders'),

  createFolder: (data: ContactFolderCreate) =>
    request<ContactFolder>('/folders/', { method: 'POST', body: JSON.stringify(data) }),

  updateFolder: (id: number, data: ContactFolderUpdate) =>
    request<ContactFolder>(`/folders/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  deleteFolder: (id: number) =>
    request<void>(`/folders/${id}`, { method: 'DELETE', _entityId: id }),

  reorderFolders: (ids: number[]) =>
    request<ContactFolder[]>('/folders/reorder', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),

  bulkUpdate: (data: BulkUpdateRequest) =>
    request<{ updated: number }>('/contacts/bulk-update', { method: 'PATCH', body: JSON.stringify(data) }),

  getTypeTemplates: (sphere?: string) => {
    const qs = sphere ? `?sphere=${sphere}` : ''
    return request<ContactTypeTemplate[]>(`/contacts/contact-types${qs}`)
  },

  createTypeTemplate: (data: ContactTypeTemplateCreate) =>
    request<ContactTypeTemplate>('/contacts/contact-types', { method: 'POST', body: JSON.stringify(data) }),

  updateTypeTemplate: (id: number, data: ContactTypeTemplateUpdate) =>
    request<ContactTypeTemplate>(`/contacts/contact-types/${id}`, { method: 'PATCH', body: JSON.stringify(data), _entityId: id }),

  deleteTypeTemplate: (id: number) =>
    request<void>(`/contacts/contact-types/${id}`, { method: 'DELETE', _entityId: id }),

  getDuplicates: (contactId?: number) => {
    const qs = contactId ? `?contact_id=${contactId}` : ''
    return request<DuplicateGroup[]>(`/contacts/duplicates${qs}`)
  },

  getTimeline: (contactId: number) =>
    request<TimelineEvent[]>(`/contacts/${contactId}/timeline`),

  getNotes: (contactId: number) =>
    request<ContactNote[]>(`/contacts/${contactId}/notes`),

  createNote: (contactId: number, data: ContactNoteCreate) =>
    request<ContactNote>(`/contacts/${contactId}/notes`, { method: 'POST', body: JSON.stringify(data) }),

  deleteNote: (noteId: number) =>
    request<void>(`/contacts/notes/${noteId}`, { method: 'DELETE', _entityId: noteId }),

  exportCsv: (ids?: number[]) => {
    const qs = ids?.length ? `?ids=${ids.join(',')}` : ''
    return request<string>(`/contacts/export${qs}`, { _textResponse: true })
  },

  importCsv: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<ImportResult>('/contacts/import', { method: 'POST', body: formData })
  },
}

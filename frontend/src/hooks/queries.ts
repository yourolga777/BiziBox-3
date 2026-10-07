import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { channelApi, contactApi, messageApi, taskApi, fetchMetrics, isOfflineError, requestOptimistic } from '../api/client'
import { reminderApi } from '../api/reminders'
import { saveMessages, getMessagesFromCache, getMessageFromCache } from '../offline/db'
import { saveContacts, getContactsFromCache, getContactFromCache } from '../offline/db'
import { saveTasks, getTasksFromCache, getTaskFromCache } from '../offline/db'
import { incrementalFetch } from '../offline/merge'
import { enqueueOptimistic } from '../offline/optimistic'
import type { Contact, ContactCreate, ContactFolderCreate, ContactFolderUpdate, ContactUpdate, ContactsQueryParams } from '../types/contact'
import type { Message, MessageUpdate } from '../types/message'
import type { Task, TaskCreate, TaskUpdate } from '../types/task'

export function useMessagesQuery(params?: { contact_id?: number; channel?: string; unread?: boolean; skip?: number; limit?: number; min_id?: number }, opts?: { refetchInterval?: number }) {
  const qc = useQueryClient()
  const queryKey = ['messages', params] as const
  return useQuery({
    queryKey,
    queryFn: () => incrementalFetch(
      qc,
      queryKey,
      (minId) => messageApi.getAll({ ...params, min_id: minId }),
      (msgs) => { saveMessages(msgs).catch(() => {}) },
    ),
    refetchInterval: opts?.refetchInterval,
  })
}

export function useInboxMessagesQuery(opts?: { refetchInterval?: number }) {
  const qc = useQueryClient()
  const queryKey = ['messages', 'inbox'] as const
  return useQuery({
    queryKey,
    queryFn: () => incrementalFetch(
      qc,
      queryKey,
      (minId) => messageApi.getInbox(minId ? { min_id: minId } : undefined),
      (msgs) => { saveMessages(msgs).catch(() => {}) },
    ),
    refetchInterval: opts?.refetchInterval,
  })
}

export function useThreadsQuery(opts?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: ['threads'],
    queryFn: () => messageApi.getThreads(),
    refetchInterval: opts?.refetchInterval,
  })
}

export function useSpamMessagesQuery(opts?: { enabled?: boolean; refetchInterval?: number }) {
  const qc = useQueryClient()
  const queryKey = ['messages', 'spam'] as const
  return useQuery({
    queryKey,
    queryFn: () => incrementalFetch(
      qc,
      queryKey,
      (minId) => messageApi.getSpam(minId ? { min_id: minId } : undefined),
      (msgs) => { saveMessages(msgs).catch(() => {}) },
    ),
    enabled: opts?.enabled !== false,
    refetchInterval: opts?.refetchInterval,
  })
}

export function useSpamCountQuery(refetchInterval?: number) {
  return useQuery({
    queryKey: ['messages', 'spam', 'count'],
    queryFn: () => messageApi.getSpamCount(),
    refetchInterval,
    retry: false,
  })
}

export function useMessageSearchQuery(q: string) {
  return useQuery({
    queryKey: ['messages', 'search', q],
    queryFn: () => messageApi.search(q),
    enabled: q.trim().length > 0,
  })
}

export function useMessageDetailQuery(id: number | undefined) {
  return useQuery({
    queryKey: ['message', id],
    queryFn: async (): Promise<Message> => {
      try {
        const data = await messageApi.getById(id!)
        saveMessages([data]).catch(() => {})
        return data
      } catch (err) {
        if ((!navigator.onLine || isOfflineError(err)) && id) {
          const cached = await getMessageFromCache(id)
          if (cached) return cached as Message
        }
        throw err
      }
    },
    enabled: !!id,
  })
}

export function useDialogQuery(contactId: number | undefined) {
  return useQuery({
    queryKey: ['dialog', contactId],
    queryFn: async (): Promise<Message[]> => {
      try {
        const data = await messageApi.getDialog(contactId!)
        if (Array.isArray(data) && data.length > 0) {
          saveMessages(data).catch(() => {})
        }
        return data
      } catch (err) {
        if (!navigator.onLine || isOfflineError(err)) {
          const cached = await getMessagesFromCache()
          const cid = contactId!
          return cached.filter((m) => {
            const msg = m as Message
            return msg.contact_id === cid
          }) as unknown as Message[]
        }
        throw err
      }
    },
    enabled: !!contactId,
  })
}

export function useContactsQuery(params?: ContactsQueryParams) {
  return useQuery({
    queryKey: ['contacts', params],
    queryFn: async (): Promise<Contact[]> => {
      try {
        const data = await contactApi.getAll(params)
        if (Array.isArray(data) && data.length > 0) {
          saveContacts(data).catch(() => {})
        }
        return data
      } catch (err) {
        if (!navigator.onLine || isOfflineError(err)) {
          const cached = await getContactsFromCache()
          return cached as Contact[]
        }
        throw err
      }
    },
    placeholderData: (prev) => prev,
  })
}

export function useContactQuery(id: number | undefined) {
  return useQuery({
    queryKey: ['contact', id],
    queryFn: async () => {
      try {
        const data = await contactApi.getById(id!)
        saveContacts([data]).catch(() => {})
        return data
      } catch (err) {
        if ((!navigator.onLine || isOfflineError(err)) && id) {
          const cached = await getContactFromCache(id)
          if (cached) return cached as Contact
        }
        throw err
      }
    },
    enabled: !!id,
  })
}

export function useCreateContactMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: ContactCreate) => {
      const body = JSON.stringify(data)
      return requestOptimistic<Contact>(
        '/contacts/',
        { method: 'POST', body },
          () =>
            enqueueOptimistic(data, (d, localId) => {
              const now = new Date().toISOString()
              return {
                id: localId,
                name: d.name ?? null,
                phone: d.phone ?? null,
                email: d.email ?? null,
                telegram_id: d.telegram_id ?? null,
                telegram_username: d.telegram_username ?? null,
                is_known: false,
                is_favorite: d.is_favorite ?? false,
                life_sphere: d.life_sphere ?? null,
                contact_types: [],
                contact_type_ids: [],
                notes: d.notes ?? null,
                channel_types: [],
                folder_id: null,
                last_message_at: null,
                deleted_at: null,
                created_at: now,
                updated_at: now,
              } as Contact
            }, saveContacts, '/contacts'),
      )
    },

    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['contacts'] })
      const previous = qc.getQueryData<Contact[]>(['contacts'])
      return { previous }
    },

    onError: (err, _data, context) => {
      if (!isOfflineError(err)) {
        qc.setQueryData(['contacts'], context?.previous)
      }
    },

    onSuccess: (result) => {
      if ('__offline' in result) {
        qc.setQueryData<Contact[]>(['contacts'], (old) => {
          if (!old) return [result.entity]
          if (old.some(c => c.id === result.entity.id)) return old
          return [...old, result.entity]
        })
      } else {
        qc.setQueryData<Contact[]>(['contacts'], (old) => {
          if (!old) return [result]
          const withoutFake = old.filter(c => c.id >= 0 && c.id !== result.id)
          return [...withoutFake, result]
        })
      }
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['contacts'] })
    },
  })
}

export function useUpdateContactMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ContactUpdate }) => contactApi.update(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['contacts'] })
      qc.invalidateQueries({ queryKey: ['contact', vars.id] })
    },
  })
}

export function useDeleteContactMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => contactApi.delete(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['contacts'] })
      qc.invalidateQueries({ queryKey: ['contact', id] })
    },
  })
}

export function useTasksQuery(params?: { status?: string; contact_id?: number; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['tasks', params],
    queryFn: async () => {
      try {
        const data = await taskApi.getAll(params)
        if (Array.isArray(data) && data.length > 0) {
          saveTasks(data).catch(() => {})
        }
        return data
      } catch (err) {
        if (!navigator.onLine || isOfflineError(err)) {
          const cached = await getTasksFromCache()
          return cached as Task[]
        }
        throw err
      }
    },
  })
}

export function useTaskQuery(id: number | undefined) {
  return useQuery({
    queryKey: ['task', id],
    queryFn: async () => {
      try {
        const data = await taskApi.getById(id!)
        saveTasks([data]).catch(() => {})
        return data
      } catch (err) {
        if ((!navigator.onLine || isOfflineError(err)) && id) {
          const cached = await getTaskFromCache(id)
          if (cached) return cached as Task
        }
        throw err
      }
    },
    enabled: !!id,
  })
}

export function useCreateTaskMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (data: TaskCreate) => {
      const body = JSON.stringify(data)
      return requestOptimistic<Task>(
        '/tasks/',
        { method: 'POST', body },
        () =>
          enqueueOptimistic(data, (d, localId) => {
            const now = new Date().toISOString()
            return {
              id: localId,
              contact_id: d.contact_id ?? null,
              title: d.title,
              description: d.description ?? null,
              status: d.status ?? 'new',
              due_date: d.due_date ?? null,
              reminder_minutes: d.reminder_minutes ?? null,
              recurrence: d.recurrence ?? null,
              created_at: now,
              updated_at: now,
            } as Task
          }, saveTasks, '/tasks'),
      )
    },

    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ['tasks'] })
      const previous = qc.getQueryData<Task[]>(['tasks'])
      return { previous }
    },

    onError: (err, _data, context) => {
      if (!isOfflineError(err)) {
        qc.setQueryData(['tasks'], context?.previous)
      }
    },

    onSuccess: (result) => {
      if ('__offline' in result) {
        qc.setQueryData<Task[]>(['tasks'], (old) => {
          if (!old) return [result.entity]
          if (old.some(t => t.id === result.entity.id)) return old
          return [...old, result.entity]
        })
      } else {
        qc.setQueryData<Task[]>(['tasks'], (old) => {
          if (!old) return [result]
          const withoutFake = old.filter(t => t.id >= 0 && t.id !== result.id)
          return [...withoutFake, result]
        })
      }
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useUpdateTaskMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TaskUpdate }) => taskApi.update(id, data),
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey: ['tasks'] })
      const previous = qc.getQueryData<Task[]>(['tasks'])
      qc.setQueryData<Task[]>(['tasks'], (old) => {
        if (!old) return old
        return old.map((t) => (t.id === id ? { ...t, ...data } : t))
      })
      return { previous }
    },
    onError: (err, _vars, context) => {
      if (!isOfflineError(err) && context?.previous !== undefined) {
        qc.setQueryData(['tasks'], context.previous)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useDeleteTaskMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => taskApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
}

export function useRestoreTaskMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => taskApi.restore(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

export function useChannelsQuery() {
  return useQuery({
    queryKey: ['channels'],
    queryFn: () => channelApi.getAll(),
  })
}

export function useDashboardMetricsQuery(refetchInterval?: number) {
  return useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: fetchMetrics,
    refetchInterval,
  })
}

export function useUpdateMessageMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MessageUpdate }) => messageApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['messages'] }),
  })
}

export function useFoldersQuery() {
  return useQuery({
    queryKey: ['folders'],
    queryFn: () => contactApi.getFolders(),
  })
}

export function useCreateFolderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ContactFolderCreate) => contactApi.createFolder(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['folders'] }),
  })
}

export function useUpdateFolderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ContactFolderUpdate }) =>
      contactApi.updateFolder(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['folders'] }),
  })
}

export function useDeleteFolderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => contactApi.deleteFolder(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['folders'] }),
  })
}

export function useNotesQuery(contactId: number | undefined) {
  return useQuery({
    queryKey: ['notes', contactId],
    queryFn: () => contactApi.getNotes(contactId!),
    enabled: !!contactId,
  })
}

export function useCreateNoteMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ contactId, data }: { contactId: number; data: { content: string; author?: string | null } }) =>
      contactApi.createNote(contactId, data),
    onSuccess: (_d, vars) => qc.invalidateQueries({ queryKey: ['notes', vars.contactId] }),
  })
}

export function useDeleteNoteMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ contactId, noteId }: { contactId: number; noteId: number }) =>
      contactApi.deleteNote(noteId).then(() => contactId),
    onSuccess: (contactId) => qc.invalidateQueries({ queryKey: ['notes', contactId] }),
  })
}

export function useTimelineQuery(contactId: number | undefined) {
  return useQuery({
    queryKey: ['timeline', contactId],
    queryFn: () => contactApi.getTimeline(contactId!),
    enabled: !!contactId,
  })
}

export function useRemindersQuery(opts?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: ['reminders'],
    queryFn: () => reminderApi.getReminders(),
    refetchInterval: opts?.refetchInterval,
    retry: false,
  })
}

export function useAckReminderMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ kind, id }: { kind: string; id: number }) =>
      reminderApi.ackReminder(kind, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminders'] }),
  })
}

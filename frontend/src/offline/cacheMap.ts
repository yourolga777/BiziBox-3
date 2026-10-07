export interface CacheEntry {
  store: string
  queryKeys: string[]
}

export const CACHE_MAP: Record<string, CacheEntry> = {
  '/contacts': { store: 'contacts', queryKeys: ['contacts'] },
  '/contacts/merge': { store: 'contacts', queryKeys: ['contacts', 'contact'] },
  '/contacts/bulk-merge': { store: 'contacts', queryKeys: ['contacts', 'contact'] },
  '/contacts/bulk-update': { store: 'contacts', queryKeys: ['contacts', 'contact'] },
  '/contacts/bulk-delete': { store: 'contacts', queryKeys: ['contacts', 'contact'] },
  '/contacts/bulk-restore': { store: 'contacts', queryKeys: ['contacts', 'contact'] },
  '/contacts/import': { store: 'contacts', queryKeys: ['contacts'] },
  '/contacts/export': { store: '', queryKeys: [] },
  '/tasks': { store: 'tasks', queryKeys: ['tasks'] },
  '/tasks/bulk-delete': { store: 'tasks', queryKeys: ['tasks', 'task'] },
  '/tasks/bulk-restore': { store: 'tasks', queryKeys: ['tasks', 'task'] },
  '/messages/send': { store: 'messages', queryKeys: ['messages', 'dialog', 'inbox', 'feed'] },
  '/messages/bulk/status': { store: 'messages', queryKeys: ['messages', 'dialog', 'inbox', 'feed', 'archive', 'spam'] },
  '/messages/bulk': { store: 'messages', queryKeys: ['messages', 'dialog', 'inbox', 'feed', 'archive', 'spam'] },
  '/messages/bulk/restore': { store: 'messages', queryKeys: ['messages', 'dialog', 'inbox', 'feed', 'archive', 'spam'] },
  '/tags': { store: '', queryKeys: ['tags'] },
  '/folders': { store: '', queryKeys: ['folders'] },
}

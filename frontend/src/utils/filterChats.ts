import type { ChatFilters, ChatItem } from '../types/inbox'

export function filterChats(chats: ChatItem[], filters: ChatFilters): ChatItem[] {
  let result = chats

  if (filters.lifeSphere === 'spam') {
    result = result.filter((c) => c.contact.life_sphere === 'spam')
  } else if (filters.lifeSphere === 'channels') {
    result = result.filter((c) => c.contact.life_sphere === 'channels')
  } else if (filters.lifeSphere) {
    result = result.filter((c) => c.contact.life_sphere === filters.lifeSphere)
  } else {
    result = result.filter(
      (c) => c.contact.life_sphere !== 'spam' && c.contact.life_sphere !== 'channels',
    )
  }

  if (filters.channel) {
    result = result.filter((c) => c.channels.has(filters.channel!))
  }

  if (filters.showOnlyNew) {
    result = result.filter((c) => c.unreadCount > 0)
  }

  if (filters.folder === 'other') {
    result = result.filter((c) => c.contact.life_sphere == null && c.contact.folder_id == null)
  } else if (filters.folder != null) {
    result = result.filter((c) => c.contact.folder_id === filters.folder)
  }

  if (filters.favorites) {
    result = result.filter((c) => c.contact.is_favorite)
  }

  if (filters.searchQuery) {
    const q = filters.searchQuery.toLowerCase()
    result = result.filter((c) => {
      const nameMatch = (c.contact.name || '').toLowerCase().includes(q)
      const msgMatch = c.lastMessage.content.toLowerCase().includes(q)
      return nameMatch || msgMatch
    })
  }

  return result
}

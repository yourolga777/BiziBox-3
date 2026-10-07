import type { Contact, ContactSphere } from './contact'
import type { Message } from './message'

export interface ChatFilters {
  channel: string | null
  folder: number | 'other' | null
  showOnlyNew: boolean
  favorites: boolean
  searchQuery: string
  lifeSphere: ContactSphere | null
}

export interface ChatItem {
  contact: Contact
  lastMessage: Message
  channels: Set<string>
  unreadCount: number
}

export interface Thread {
  contact_id: number
  last_message: Message
  unread_count: number
  channels: string[]
}

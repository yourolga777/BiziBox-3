export interface MessageAttachment {
  id: number
  message_id: number
  channel_message_id?: string | null
  file_name?: string | null
  file_size?: number | null
  mime_type?: string | null
  file_path?: string | null
  created_at?: string | null
}

export interface Message {
  id: number
  contact_id: number
  contact_name?: string | null
  contact_username?: string | null
  channel: string
  channel_message_id: string | null
  reply_to?: string | null
  subject?: string | null
  content: string
  content_html?: string | null
  direction: 'incoming' | 'outgoing'
  status: 'unread' | 'read' | 'archived'
  created_at: string | null
  updated_at: string | null
  attachments?: MessageAttachment[]
  sync_pending?: boolean
  is_flagged?: boolean
  is_pinned?: boolean
  snoozed_until?: string | null
  extracted_code?: string | null
}

export interface MessageCreate {
  contact_id: number
  channel: string
  channel_message_id?: string | null
  content: string
  direction: 'incoming' | 'outgoing'
  status?: 'unread' | 'read' | 'archived'
  snoozed_until?: string | null
}

export interface MessageUpdate {
  content?: string
  status?: 'unread' | 'read' | 'archived'
  contact_id?: number
  is_flagged?: boolean
  is_pinned?: boolean
  snoozed_until?: string | null
}

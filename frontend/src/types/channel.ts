export interface Channel {
  id: number
  type: string
  name: string
  is_connected: boolean
  last_polled_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DownloadResponse {
  new_messages: number
  last_polled_at: string | null
}

export interface ChannelHealth {
  channel_id: number
  type: string
  is_connected_db: boolean
  adapter_alive: boolean
  needs_reconnect: boolean
}

export interface TelegramConnectRequest {
  phone: string
  via?: 'auto' | 'sms' | 'app'
}

export interface TelegramConnectResponse {
  status: string
  message: string
  channel_id?: number
  phone_code_hash?: string
  code_type?: 'app' | 'sms' | 'call'
  next_type?: 'sms' | 'call' | 'flashcall' | 'missed_call'
  timeout?: number
}

export interface TelegramConfirmRequest {
  channel_id: number
  code: string
  phone_code_hash: string
}

export interface TelegramConfirmResponse {
  status: string
  message: string
  channel_id?: number
  phone_code_hash?: string
  retry_count?: number
}

export interface TelegramPasswordRequest {
  channel_id: number
  password: string
}

export interface TelegramResendRequest {
  channel_id: number
  phone_code_hash: string
}

export interface TelegramResendResponse {
  status: string
  phone_code_hash: string
  code_type: 'app' | 'sms' | 'call'
  next_type?: 'sms' | 'call' | 'flashcall' | 'missed_call'
  timeout?: number
  message: string
}

export interface EmailConnectRequest {
  email: string
  password: string
  imap_host: string
  smtp_host: string
  imap_port?: number
  smtp_port?: number
}

export interface VkConnectRequest {
  group_id?: number
  token?: string
}

export interface SendReplyRequest {
  message_id: number
  content: string
  recipient?: string
}

export interface SendMessageRequest {
  contact_id: number
  channel: string
  content: string
  recipient?: string
}

export interface PulseAnimation {
  type: string
  intensity: number
}

export interface MetricsResponse {
  total_messages_today: number
  total_tasks_today: number
  new_contacts_today: number
  total_messages: number
  total_tasks: number
  total_contacts: number
  messages_yesterday: number
  tasks_yesterday: number
  contacts_yesterday: number
  unread_messages: number
  unread_chats: number
  answered_messages: number
  completed_tasks: number
  new_messages: number
  new_tasks: number
  messages_today_active: number
  active_tasks: number
  channel_distribution: { channel: string; count: number }[]
  top_contacts: { contact_id: number; contact_name: string | null; message_count: number }[]
  last_activity: string
  last_updated: string
  pulse_animation: PulseAnimation
}

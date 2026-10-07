export type ContactSphere = 'personal' | 'work' | 'channels' | 'spam'

export type ContactIdentifierChannel = 'phone' | 'email' | 'telegram_id' | 'telegram_username'

export interface ContactIdentifier {
  channel: ContactIdentifierChannel
  value: string
}

export interface ContactFolderRef {
  id: number
  name: string
  color?: string | null
  sphere?: ContactSphere | null
  parent_id?: number | null
}

export interface Contact {
  id: number
  name: string | null
  phone: string | null
  email: string | null
  telegram_id: string | null
  telegram_username: string | null
  is_known: boolean
  is_favorite: boolean
  is_blocked?: boolean
  life_sphere: ContactSphere | null
  contact_types: string[]
  contact_type_ids: number[]
  birthday?: string | null
  notes: string | null
  channel_types: string[]
  folder_id: number | null
  last_message_at: string | null
  deleted_at: string | null
  created_at: string | null
  updated_at: string | null
  message_count?: number
  task_count?: number
  identifiers?: ContactIdentifier[]
  spheres?: string[]
  folders?: ContactFolderRef[]
}

export type ContactSortBy = 'name' | 'created_at' | 'message_count' | 'last_activity' | 'first_message' | 'has_tasks'
export type ContactSubsection = 'new'

export interface ContactsQueryParams {
  search?: string
  channel?: string
  subsection?: ContactSubsection
  life_sphere?: ContactSphere
  contact_type_ids?: number[]
  folder_id?: number
  is_favorite?: boolean
  unclassified?: boolean
  sort_by?: ContactSortBy
  sort_order?: 'asc' | 'desc'
  skip?: number
  limit?: number
}

export interface ContactCreate {
  name?: string | null
  phone?: string | null
  email?: string | null
  telegram_id?: string | null
  telegram_username?: string | null
  notes?: string | null
  life_sphere?: ContactSphere | null
  contact_type_ids?: number[] | null
  birthday?: string | null
  is_known?: boolean | null
  is_favorite?: boolean | null
  folder_id?: number | null
  folder_ids?: number[] | null
}

export interface ContactUpdate {
  name?: string | null
  phone?: string | null
  email?: string | null
  telegram_id?: string | null
  telegram_username?: string | null
  is_known?: boolean | null
  is_favorite?: boolean | null
  life_sphere?: ContactSphere | null
  contact_type_ids?: number[] | null
  birthday?: string | null
  folder_id?: number | null
  folder_ids?: number[] | null
  notes?: string | null
}

export interface ContactFolder {
  id: number
  name: string
  color: string | null
  sort_order: number
  is_default: boolean
  category_key: string | null
  sphere: ContactSphere | null
  parent_id: number | null
  created_at: string | null
  updated_at?: string | null
}

export interface ContactFolderCreate {
  name: string
  color?: string | null
  sort_order?: number
  category_key?: string | null
  sphere?: ContactSphere | null
  parent_id?: number | null
}

export interface ContactFolderUpdate {
  name?: string
  color?: string | null
  sort_order?: number
  category_key?: string | null
  sphere?: ContactSphere | null
  parent_id?: number | null
}

export interface BulkUpdateRequest {
  ids: number[]
  is_known?: boolean | null
  folder_id?: number | null
  is_favorite?: boolean | null
  life_sphere?: ContactSphere | null
  contact_type_ids?: number[] | null
}

export interface ContactTypeTemplate {
  id: number
  sphere: ContactSphere
  name: string
  slug: string | null
  sort_order: number
  is_custom: boolean
  is_system: boolean
}

export interface ContactTypeTemplateCreate {
  sphere: ContactSphere
  name: string
}

export interface ContactTypeTemplateUpdate {
  name?: string
}

export interface DuplicateGroup {
  contacts: Contact[]
  reason: string
}

export interface TimelineEvent {
  type: string
  title: string
  subtitle: string
  created_at: string | null
  link: string | null
}

export interface ContactNote {
  id: number
  content: string
  author: string | null
  created_at: string | null
}

export interface ContactNoteCreate {
  content: string
  author?: string | null
}

export interface ImportResult {
  created: number
  updated: number
}

export interface DashboardChannelStats {
  channel: string
  count: number
}

export interface DashboardContactStats {
  contact_id: number
  contact_name: string | null
  message_count: number
}
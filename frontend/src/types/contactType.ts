import type { ContactSphere } from './contact'

export const CONTACT_SPHERES: ContactSphere[] = [
  'work',
  'personal',
  'channels',
  'spam',
]

export const CONTACT_SPHERE_META: Record<ContactSphere | 'other', { label: string; color: string; bg: string }> = {
  work: { label: 'Работа', color: 'text-blue-700', bg: 'bg-blue-100' },
  personal: { label: 'Личное', color: 'text-green-700', bg: 'bg-green-100' },
  channels: { label: 'Каналы', color: 'text-cyan-700', bg: 'bg-cyan-100' },
  spam: { label: 'Спам', color: 'text-gray-600', bg: 'bg-gray-100' },
  other: { label: 'Другое', color: 'text-gray-500', bg: 'bg-gray-50' },
}

export const CONTACT_SPHERE_FILTERS: { key: ContactSphere | ''; label: string }[] = [
  { key: '', label: 'Все сферы' },
  ...CONTACT_SPHERES.map((s) => ({ key: s, label: CONTACT_SPHERE_META[s].label })),
]

export function contactSphereLabel(value: string | null | undefined): string {
  if (value && value in CONTACT_SPHERE_META) return CONTACT_SPHERE_META[value as ContactSphere].label
  return 'Другое'
}

export function contactSphereMeta(value: string | null | undefined): { label: string; color: string; bg: string } {
  if (value && value in CONTACT_SPHERE_META) return CONTACT_SPHERE_META[value as ContactSphere]
  return { label: 'Другое', color: 'text-gray-500', bg: 'bg-gray-50' }
}
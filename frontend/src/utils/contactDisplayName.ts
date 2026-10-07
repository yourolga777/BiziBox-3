export function displayName(contact: { telegram_username?: string | null; name?: string | null; id?: number; email?: string | null }): string {
  if (contact.name) return contact.name
  if (contact.telegram_username) return `@${contact.telegram_username}`
  return `Контакт #${contact.id}`
}

export function displayNameShort(contact: { telegram_username?: string | null; name?: string | null; id?: number; email?: string | null }): string | null {
  if (contact.name) return contact.name
  return contact.telegram_username ? `@${contact.telegram_username}` : null
}

import { describe, it, expect } from 'vitest'
import { displayName, displayNameShort } from '../contactDisplayName'

describe('displayName', () => {
  it('prioritizes name over telegram_username and id', () => {
    expect(displayName({ telegram_username: 'johnny', name: 'John', id: 5 })).toBe('John')
  })

  it('falls back to name', () => {
    expect(displayName({ name: 'John', id: 5 })).toBe('John')
  })

  it('falls back to telegram username when no name', () => {
    expect(displayName({ telegram_username: 'johnny', name: null, id: 5 })).toBe('@johnny')
  })

  it('falls back to id when no username and name is null', () => {
    expect(displayName({ name: null, id: 5 })).toBe('Контакт #5')
  })

  it('does not crash with empty contact', () => {
    expect(displayName({})).toBe('Контакт #undefined')
  })
})

describe('displayNameShort', () => {
  it('returns name when present over username', () => {
    expect(displayNameShort({ telegram_username: 'ann', name: 'Anna' })).toBe('Anna')
  })

  it('returns username when no name', () => {
    expect(displayNameShort({ telegram_username: 'ann', name: null })).toBe('@ann')
  })

  it('returns name when no username', () => {
    expect(displayNameShort({ name: 'Anna' })).toBe('Anna')
  })

  it('returns null when email-only contact has no username', () => {
    expect(displayNameShort({ email: 'a@b.ru' })).toBeNull()
  })
})

import { describe, it, expect } from 'vitest'
import { filterChats } from '../filterChats'
import type { ChatItem } from '../../types/inbox'
import type { Contact } from '../../types/contact'
import type { Message } from '../../types/message'

function c(overrides: Partial<Contact> = {}): Contact {
  return {
    id: 1,
    name: 'Тест',
    phone: null,
    email: null,
    telegram_id: null,
    telegram_username: null,
    is_known: true,
    is_favorite: false,
    life_sphere: null,
    notes: null,
    channel_types: ['telegram'],
    contact_types: [],
    contact_type_ids: [],
    folder_id: null,
    last_message_at: null,
    deleted_at: null,
    created_at: '2026-01-01',
    updated_at: null,
    ...overrides,
  }
}

function m(overrides: Partial<Message> = {}): Message {
  return {
    id: 1,
    contact_id: 1,
    channel: 'telegram',
    channel_message_id: 'msg-1',
    content: 'Привет',
    direction: 'incoming',
    status: 'read',
    contact_name: 'Тест',
    contact_username: null,
    created_at: '2026-01-01',
    updated_at: null,
    ...overrides,
  }
}

function makeChat(contactOverrides: Partial<Contact> = {}, msgOverrides: Partial<Message> = {}, unreadCount = 0): ChatItem {
  const contact = c(contactOverrides)
  const message = m({ ...msgOverrides, contact_id: contact.id })
  return {
    contact,
    lastMessage: message,
    channels: new Set([message.channel]),
    unreadCount,
  }
}

function df(overrides: Partial<import('../../types/inbox').ChatFilters> = {}): import('../../types/inbox').ChatFilters {
  return { channel: null, folder: null, showOnlyNew: false, favorites: false, searchQuery: '', lifeSphere: null, ...overrides }
}

function makeChats(): ChatItem[] {
  return [
    makeChat({ id: 1, name: 'Рабочий1', is_known: true, life_sphere: 'work', folder_id: 1 }, { content: 'Заказ', channel: 'telegram' }),
    makeChat({ id: 2, name: 'Личный1', is_known: true, life_sphere: 'personal', folder_id: 2 }, { content: 'Привет', channel: 'telegram' }),
    makeChat({ id: 3, name: 'Новый', is_known: false, life_sphere: null }, { content: 'Вопрос', channel: 'email' }),
    makeChat({ id: 4, name: 'Спамер', life_sphere: 'spam', is_known: false }, { content: 'Купи', channel: 'telegram' }),
    makeChat({ id: 5, name: 'Избранный', is_favorite: true, is_known: true, life_sphere: 'work', folder_id: 1 }, { content: 'Важно', channel: 'telegram' }),
    makeChat({ id: 6, name: 'СЗадачей', is_known: true, life_sphere: 'work', task_count: 1 }, { content: 'Проект', channel: 'telegram' }),
  ]
}

describe('filterChats', () => {
  const BASE = makeChats()

  it('исключает спам', () => {
    const result = filterChats(BASE, df())
    expect(result).toHaveLength(5)
    expect(result.find((c) => c.contact.name === 'Спамер')).toBeUndefined()
  })

  it('фильтрует по каналу', () => {
    const result = filterChats(BASE, df({ channel: 'email' }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Новый')
  })

  it('фильтрует по папке (folder_id)', () => {
    const result = filterChats(BASE, df({ folder: 2 }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Личный1')
  })

  it('фильтрует только новые (непрочитанные)', () => {
    const base = [
      makeChat({ id: 1, name: 'Прочитан', is_known: true }, {}, 0),
      makeChat({ id: 2, name: 'Непрочитан', is_known: true }, {}, 3),
      makeChat({ id: 3, name: 'НепрочитанНовый', is_known: false }, {}, 1),
    ]
    const result = filterChats(base, df({ showOnlyNew: true }))
    expect(result).toHaveLength(2)
    expect(result.map(c => c.contact.name).sort()).toEqual(['Непрочитан', 'НепрочитанНовый'])
  })

  it('фильтрует "Другое" (life_sphere/папка не заданы)', () => {
    const result = filterChats(BASE, df({ folder: 'other' }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Новый')
  })

  it('ищет по имени', () => {
    const result = filterChats(BASE, df({ searchQuery: 'личный' }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Личный1')
  })

  it('ищет по тексту сообщения', () => {
    const result = filterChats(BASE, df({ searchQuery: 'вопрос' }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Новый')
  })

  it('комбинирует фильтры: папка + канал', () => {
    const result = filterChats(BASE, df({ channel: 'telegram', folder: 1 }))
    expect(result).toHaveLength(2)
    expect(result.map(c => c.contact.name).sort()).toEqual(['Избранный', 'Рабочий1'])
  })

  it('пустые фильтры возвращают всё кроме спама', () => {
    const result = filterChats(BASE, df())
    expect(result).toHaveLength(5)
  })

  it('пустой результат при несовместимых фильтрах', () => {
    const result = filterChats(BASE, df({ channel: 'email', folder: 1 }))
    expect(result).toHaveLength(0)
  })

  it('фильтрует избранное (is_favorite)', () => {
    const result = filterChats(BASE, df({ favorites: true }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Избранный')
  })

  it('не показывает спам при фильтре избранное', () => {
    const base = [
      makeChat({ id: 20, name: 'СпамИзбранный', is_favorite: true, life_sphere: 'spam' }, { content: 'Реклама', channel: 'telegram' }),
      makeChat({ id: 21, name: 'НормИзбранный', is_favorite: true, is_known: true }, { content: 'Привет', channel: 'telegram' }),
    ]
    const result = filterChats(base, df({ favorites: true }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('НормИзбранный')
  })

  it('negative: избранное не включает не-favorite', () => {
    const result = filterChats(BASE, df({ favorites: true }))
    result.forEach(c => {
      expect(c.contact.is_favorite).toBe(true)
    })
  })

  it('фильтрует по каналу, когда в чате смешанные каналы', () => {
    const mixed = makeChat(
      { id: 7, name: 'Смешанный', is_known: true },
      { content: 'последнее telegram', channel: 'telegram' },
    )
    mixed.channels = new Set(['telegram', 'email'])
    const base = [...BASE, mixed]
    const result = filterChats(base, df({ channel: 'email' }))
    expect(result).toHaveLength(2)
    expect(result.map(c => c.contact.name).sort()).toEqual(['Новый', 'Смешанный'])
  })

  it('фильтрует по сфере (personal)', () => {
    const base = [
      makeChat({ id: 1, name: 'Личный', is_known: true, life_sphere: 'personal' }, { content: 'x' }),
      makeChat({ id: 2, name: 'Рабочий', is_known: true, life_sphere: 'work' }, { content: 'y' }),
      makeChat({ id: 3, name: 'Другое', is_known: true, life_sphere: null }, { content: 'z' }),
    ]
    const result = filterChats(base, df({ lifeSphere: 'personal' }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Личный')
  })

  it('фильтр по сфере spam показывает только спам', () => {
    const base = [
      makeChat({ id: 1, name: 'Спам1', life_sphere: 'spam' }, { content: 'x' }),
      makeChat({ id: 2, name: 'НеСпам', life_sphere: null }, { content: 'y' }),
      makeChat({ id: 3, name: 'Норм', is_known: true, life_sphere: 'work' }, { content: 'z' }),
    ]
    const result = filterChats(base, df({ lifeSphere: 'spam' }))
    expect(result).toHaveLength(1)
    expect(result[0].contact.name).toBe('Спам1')
  })
})

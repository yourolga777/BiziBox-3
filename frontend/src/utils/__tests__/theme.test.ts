import { describe, it, expect, beforeEach } from 'vitest'
import { applyTheme, getStoredTheme, storeTheme } from '../theme'

describe('theme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  it('применяет тёмную тему через класс dark (AC3)', () => {
    applyTheme('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('снимает класс dark для светлой темы', () => {
    document.documentElement.classList.add('dark')
    applyTheme('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('сохраняет тему в localStorage (AC2)', () => {
    storeTheme('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(getStoredTheme()).toBe('dark')
  })

  it('возвращает light по умолчанию при отсутствии значения (AC4 negative)', () => {
    expect(getStoredTheme()).toBe('light')
  })
})

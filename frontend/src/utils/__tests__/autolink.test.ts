import { describe, it, expect } from 'vitest'
import { autolinkText } from '../autolink'

describe('autolinkText', () => {
  it('ссылается на email', () => {
    const html = autolinkText('напиши на test@example.com пожалуйста')
    expect(html).toContain('href="mailto:test@example.com"')
    expect(html).toContain('>test@example.com</a>')
  })

  it('ссылается на @username', () => {
    const html = autolinkText('смотри @vasyapetrov пост')
    expect(html).toContain('href="https://t.me/vasyapetrov"')
    expect(html).toContain('>@vasyapetrov</a>')
  })

  it('экранирует XSS', () => {
    const html = autolinkText('<script>alert(1)</script>')
    expect(html).not.toContain('<script>')
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('не ссылается на @ внутри слова', () => {
    const html = autolinkText('email@example.com')
    expect(html).toContain('href="mailto:email@example.com"')
    expect(html).not.toContain('t.me')
  })

  it('ссылается на URL и показывает домен', () => {
    const html = autolinkText('смотри https://example.com/very/long/path?q=1')
    expect(html).toContain('href="https://example.com/very/long/path?q=1"')
    expect(html).toContain('>example.com</a>')
  })

  it('ссылается на www-адрес', () => {
    const html = autolinkText('зайди на www.example.com')
    expect(html).toContain('href="https://www.example.com"')
    expect(html).toContain('>example.com</a>')
  })
})
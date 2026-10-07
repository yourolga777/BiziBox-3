const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g
const USERNAME_RE = /(?<![\w@])(@[A-Za-z0-9_]{1,32})(?![\w@])/g
const URL_RE = /(?:https?:\/\/|www\.)[^\s<>"'`]+/gi
const ESCAPE_RE = /[&<>"']/g

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }
  return text.replace(ESCAPE_RE, (ch) => map[ch])
}

function displayDomain(url: string): string {
  try {
    const u = new URL(url.startsWith('http') ? url : `https://${url}`)
    return u.hostname.replace(/^www\./, '')
  } catch {
    return url.replace(/^https?:\/\//, '').replace(/^www\./, '')
  }
}

/** Автоссылки на URL, email и @username в тексте. Возвращает безопасный HTML. */
export function autolinkText(text: string): string {
  const placeholders: string[] = []

  const withUrls = text.replace(URL_RE, (url) => {
    const href = url.startsWith('http') ? url : `https://${url}`
    const label = displayDomain(url)
    placeholders.push(
      `<a href="${escapeHtml(href)}" class="msg-link" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`,
    )
    return `\u0000${placeholders.length - 1}\u0000`
  })

  const escaped = escapeHtml(withUrls)
  const emailLinked = escaped.replace(EMAIL_RE, (email) => {
    const href = `mailto:${email}`
    return `<a href="${href}" class="underline" target="_blank" rel="noopener noreferrer">${email}</a>`
  })
  const usernameLinked = emailLinked.replace(USERNAME_RE, (username) => {
    const slug = username.slice(1)
    const href = `https://t.me/${slug}`
    return `<a href="${href}" class="underline" target="_blank" rel="noopener noreferrer">${username}</a>`
  })

  // \u0000 используется как безопасный sentinel-разделитель для URL-плейсхолдеров
  // eslint-disable-next-line no-control-regex
  return usernameLinked.replace(/\u0000(\d+)\u0000/g, (_m, i: string) => placeholders[Number(i)] ?? '')
}

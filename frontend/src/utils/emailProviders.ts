export interface EmailProviderConfig {
  label: string
  imap_host: string
  imap_port: number
  smtp_host: string
  smtp_port: number
  app_password_url?: string
}

export const EMAIL_PROVIDERS: Record<string, EmailProviderConfig> = {
  gmail: {
    label: 'Gmail',
    imap_host: 'imap.gmail.com',
    imap_port: 993,
    smtp_host: 'smtp.gmail.com',
    smtp_port: 465,
    app_password_url: 'https://myaccount.google.com/apppasswords',
  },
  yandex: {
    label: 'Yandex',
    imap_host: 'imap.yandex.ru',
    imap_port: 993,
    smtp_host: 'smtp.yandex.ru',
    smtp_port: 465,
    app_password_url: 'https://id.yandex.ru/security/app-passwords',
  },
  mailru: {
    label: 'Mail.ru',
    imap_host: 'imap.mail.ru',
    imap_port: 993,
    smtp_host: 'smtp.mail.ru',
    smtp_port: 465,
    app_password_url: 'https://account.mail.ru/user/2-step-auth/passwords',
  },
  outlook: {
    label: 'Outlook',
    imap_host: 'outlook.office365.com',
    imap_port: 993,
    smtp_host: 'smtp.office365.com',
    smtp_port: 587,
    app_password_url: 'https://account.live.com/proofs/manage/additional',
  },
  yahoo: {
    label: 'Yahoo',
    imap_host: 'imap.mail.yahoo.com',
    imap_port: 993,
    smtp_host: 'smtp.mail.yahoo.com',
    smtp_port: 465,
    app_password_url: 'https://login.yahoo.com/account/security',
  },
  icloud: {
    label: 'iCloud',
    imap_host: 'imap.mail.me.com',
    imap_port: 993,
    smtp_host: 'smtp.mail.me.com',
    smtp_port: 587,
    app_password_url: 'https://appleid.apple.com',
  },
}

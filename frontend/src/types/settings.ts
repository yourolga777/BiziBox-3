export type NetworkMode = 'direct' | 'system_vpn' | 'custom_proxy'

export interface ProxyConfig {
  mode?: NetworkMode
  enabled?: boolean
  type?: string
  host?: string | null
  port?: number | null
  username?: string | null
  password?: string | null
  secret?: string | null
}

export interface Settings {
  telegram_poll_interval: number
  email_poll_interval: number
  theme: 'light' | 'dark'
  proxy_config?: ProxyConfig | null
  [key: string]: unknown
}

export interface SettingsUpdate {
  values: Record<string, unknown>
}


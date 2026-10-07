import { request } from './client'
import type { Settings, SettingsUpdate } from '../types/settings'

export interface OnboardingData {
  login?: string
  telegram?: { api_id?: number; api_hash?: string; api_hash_set?: boolean; phone?: string; password_2fa?: string }
  email?: { email?: string; password?: string; imap_host?: string; imap_port?: number; smtp_host?: string; smtp_port?: number }
  vk?: { group_id?: number; password_2fa?: string; token?: string }
  proxy?: { enabled?: boolean; type?: string; host?: string; port?: number; username?: string; password?: string; secret?: string; mode?: string }
}

export interface VpnHelpResult {
  found: boolean
  name?: string
  category?: 'system_vpn' | 'proxy' | 'mtproto' | 'unknown'
  description?: string
  advice?: string
  default_port?: string | null
  source?: 'builtin' | 'web'
  message?: string
}

export const settingsApi = {
  get: () => request<Settings>('/settings/'),

  update: (data: SettingsUpdate) =>
    request<Settings>('/settings/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  onboardingStatus: () =>
    request<{onboarded: boolean; login?: string}>('/settings/onboarding-status'),

  onboardingComplete: (data: OnboardingData) =>
    request<{ onboarded: boolean; login?: string }>('/settings/onboarding-complete', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  onboardingConfig: (login?: string) =>
    request<OnboardingData>(`/settings/onboarding-config${login ? `?login=${encodeURIComponent(login)}` : ''}`),

  vpnHelp: (name: string) =>
    request<VpnHelpResult>(`/vpn-help?name=${encodeURIComponent(name)}`),

  logout: () =>
    request<{ onboarded: boolean }>('/settings/auth/logout', {
      method: 'POST',
    }),
}

import type { Channel, ChannelHealth, DownloadResponse, EmailConnectRequest, TelegramConfirmRequest, TelegramConfirmResponse, TelegramConnectRequest, TelegramConnectResponse, TelegramPasswordRequest, TelegramResendRequest, TelegramResendResponse, VkConnectRequest } from '../types/channel'
import { request } from './client'

export const channelApi = {
  getAll: () => request<Channel[]>('/channels'),

  getById: (id: number) => request<Channel>(`/channels/${id}`),

  health: (id: number) => request<ChannelHealth>(`/channels/${id}/health`),

  connectTelegram: (data: TelegramConnectRequest) =>
    request<TelegramConnectResponse>('/channels/telegram/connect', {
      method: 'POST',
      body: JSON.stringify(data),
      _offlineEnqueue: false,
      // Бэкенд: proxy-check(3s) + connect(3×45s) + send_code(20s) — до ~165с.
      _timeoutMs: 180_000,
    }),

  confirmTelegram: (data: TelegramConfirmRequest) =>
    request<TelegramConfirmResponse>('/channels/telegram/confirm', {
      method: 'POST',
      body: JSON.stringify(data),
      _offlineEnqueue: false,
      _timeoutMs: 60_000,
    }),

  resendTelegram: (data: TelegramResendRequest) =>
    request<TelegramResendResponse>('/channels/telegram/resend', {
      method: 'POST',
      body: JSON.stringify(data),
      _offlineEnqueue: false,
      _timeoutMs: 60_000,
    }),

  submitPassword: (data: TelegramPasswordRequest) =>
    request<TelegramConfirmResponse>('/channels/telegram/password', {
      method: 'POST',
      body: JSON.stringify(data),
      _offlineEnqueue: false,
      _timeoutMs: 60_000,
    }),

  connectEmail: (data: EmailConnectRequest) =>
    request<{ status: string; message: string }>('/channels/email/connect', {
      method: 'POST',
      body: JSON.stringify(data),
      _offlineEnqueue: false,
    }),

  reconnectEmail: (data: EmailConnectRequest) =>
    request<{ status: string; message: string }>('/channels/email/reconnect', {
      method: 'POST',
      body: JSON.stringify(data),
      _offlineEnqueue: false,
    }),

  reconnectEmailStored: () =>
    request<{ status: string; message: string }>('/channels/email/reconnect-stored', {
      method: 'POST',
      body: '{}',
      _offlineEnqueue: false,
    }),

  connectVk: (data: VkConnectRequest) =>
    request<{ status: string; message: string; polling?: boolean }>('/channels/vk/connect', {
      method: 'POST',
      body: JSON.stringify(data),
      _offlineEnqueue: false,
    }),

  reconnectVkStored: () =>
    request<{ status: string; message: string }>('/channels/vk/reconnect-stored', {
      method: 'POST',
      body: '{}',
      _offlineEnqueue: false,
    }),

  delete: (id: number) =>
    request<{ status: string; message: string }>(`/channels/${id}`, {
      method: 'DELETE',
      _offlineEnqueue: false,
    }),

  download: (type: string) =>
    request<DownloadResponse>(`/channels/${type}/download`, {
      method: 'POST',
      _offlineEnqueue: false,
    }),
}

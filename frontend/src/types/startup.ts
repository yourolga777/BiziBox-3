export interface StartupChannelResult {
  type: string
  name: string
  connected: boolean
  new_messages: number
  error: string | null
}

export interface StartupLoadResult {
  channels: StartupChannelResult[]
  total_new: number
}

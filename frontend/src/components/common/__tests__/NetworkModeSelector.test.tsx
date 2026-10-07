import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import NetworkModeSelector, { type ProxyFields } from '../NetworkModeSelector'
import { settingsApi } from '../../../api/settings'
import type { NetworkMode } from '../../../types/settings'

vi.mock('../../../api/settings', () => ({
  settingsApi: { vpnHelp: vi.fn() },
}))

const fields: ProxyFields = { type: 'socks5', host: '', port: '', username: '', password: '', secret: '' }

function renderComponent(
  mode: NetworkMode = 'direct',
  onModeChange = vi.fn(),
  onFieldsChange = vi.fn(),
) {
  return render(
    <NetworkModeSelector mode={mode} fields={fields} onModeChange={onModeChange} onFieldsChange={onFieldsChange} />,
  )
}

describe('NetworkModeSelector', () => {
  it('рендерит три взаимоисключающих режима', () => {
    renderComponent()
    expect(screen.getByText('Напрямую (без VPN и прокси)')).toBeInTheDocument()
    expect(screen.getByText('Системный VPN')).toBeInTheDocument()
    expect(screen.getByText('Свой прокси')).toBeInTheDocument()
    expect(screen.getAllByRole('radio')).toHaveLength(3)
  })

  it('скрывает поля прокси, когда режим не custom_proxy', () => {
    renderComponent('direct')
    expect(screen.queryByLabelText('Хост')).toBeNull()
    expect(screen.queryByLabelText('Порт')).toBeNull()
  })

  it('показывает поля прокси при режиме custom_proxy', () => {
    renderComponent('custom_proxy')
    expect(screen.getByLabelText('Хост')).toBeInTheDocument()
    expect(screen.getByLabelText('Порт')).toBeInTheDocument()
  })

  it('вызывает onModeChange при выборе радио', () => {
    const onChange = vi.fn()
    renderComponent('direct', onChange)
    const radios = screen.getAllByRole('radio')
    fireEvent.click(radios[1])
    expect(onChange).toHaveBeenCalledWith('system_vpn')
    fireEvent.click(radios[2])
    expect(onChange).toHaveBeenCalledWith('custom_proxy')
  })

  it('ищет справку по названию сервиса', async () => {
    vi.mocked(settingsApi.vpnHelp).mockResolvedValue({
      found: true,
      name: 'v2rayN',
      category: 'proxy',
      description: 'Клиент V2Ray для Windows.',
      advice: 'Выберите «Свой прокси».',
      default_port: '10808',
      source: 'builtin',
    })
    renderComponent('direct')
    fireEvent.click(screen.getByText('Я не знаю, что у меня за сервис'))
    const input = screen.getByPlaceholderText(/v2rayN, Happ/)
    fireEvent.change(input, { target: { value: 'v2rayN' } })
    fireEvent.click(screen.getByText('Найти'))

    await waitFor(() => expect(vi.mocked(settingsApi.vpnHelp)).toHaveBeenCalledWith('v2rayN'))
    await waitFor(() => expect(screen.getByText('Клиент V2Ray для Windows.')).toBeInTheDocument())
  })

  it('показывает сообщение, если сервис не найден', async () => {
    vi.mocked(settingsApi.vpnHelp).mockResolvedValue({ found: false, message: 'Сервис не найден.' })
    renderComponent('direct')
    fireEvent.click(screen.getByText('Я не знаю, что у меня за сервис'))
    fireEvent.change(screen.getByPlaceholderText(/v2rayN, Happ/), { target: { value: 'zzz' } })
    fireEvent.click(screen.getByText('Найти'))

    await waitFor(() => expect(screen.getByText('Сервис не найден.')).toBeInTheDocument())
  })
})

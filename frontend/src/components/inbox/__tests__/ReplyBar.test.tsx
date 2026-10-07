import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ReplyBar, { type RecipientOption } from '../ReplyBar'

const baseProps = {
  text: '',
  sending: false,
  error: null,
  replyTarget: null,
  attachments: [],
  onTextChange: vi.fn(),
  onSend: vi.fn(),
  onKeyDown: vi.fn(),
  onAttachmentsChange: vi.fn(),
  onCancelReply: vi.fn(),
}

describe('ReplyBar — выбор получателя', () => {
  it('селектор скрыт, когда получатель один', () => {
    const options: RecipientOption[] = [{ value: '12345', label: 'TG ID: 12345' }]
    render(<ReplyBar {...baseProps} recipientOptions={options} recipientValue="" onRecipientChange={vi.fn()} />)
    expect(screen.queryByText('Получатель:')).toBeNull()
  })

  it('селектор скрыт без опций (negative)', () => {
    render(<ReplyBar {...baseProps} recipientOptions={[]} recipientValue="" onRecipientChange={vi.fn()} />)
    expect(screen.queryByText('Получатель:')).toBeNull()
  })

  it('селектор виден при нескольких адресах и отдаёт выбор', () => {
    const options: RecipientOption[] = [
      { value: '12345', label: 'TG ID: 12345' },
      { value: '@second', label: 'TG @: @second' },
    ]
    const onChange = vi.fn()
    render(<ReplyBar {...baseProps} recipientOptions={options} recipientValue="" onRecipientChange={onChange} />)

    const select = screen.getByLabelText('Получатель:') as HTMLSelectElement
    expect(select).toBeInTheDocument()
    expect(select.value).toBe('')
    expect(screen.getByText('По умолчанию (адрес контакта)')).toBeInTheDocument()

    fireEvent.change(select, { target: { value: '@second' } })
    expect(onChange).toHaveBeenCalledWith('@second')
  })
})

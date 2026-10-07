import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThreadList } from '../ThreadList';
import { ToastProvider } from '../../common/Toast';
import type { Message } from '../../../types/message';

function renderThreadList(ui: React.ReactElement) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

function makeMessage(overrides: Partial<Message>): Message {
  return {
    id: 1,
    contact_id: 10,
    channel: 'telegram',
    channel_message_id: 'msg_1',
    content: 'Hello',
    direction: 'incoming',
    status: 'unread',
    created_at: null,
    updated_at: null,
    ...overrides,
  };
}

describe('ThreadList', () => {
  it('renders attachment button with file name and size', () => {
    const msg = makeMessage({
      id: 5,
      attachments: [
        {
          id: 42,
          message_id: 5,
          channel_message_id: 'msg_1',
          file_name: 'report.pdf',
          file_size: 2048,
          mime_type: 'application/pdf',
        },
      ],
    });

    renderThreadList(<ThreadList messages={[msg]} />);

    const button = screen.getByRole('button', { name: /report\.pdf/i });
    expect(button).toBeInTheDocument();
    expect(button.textContent).toContain('2.0 КБ')
  });

  it('opens attachment preview dialog on click', async () => {
    const msg = makeMessage({
      id: 5,
      attachments: [
        {
          id: 42,
          message_id: 5,
          channel_message_id: 'msg_1',
          file_name: 'report.pdf',
          file_size: 2048,
          mime_type: 'application/pdf',
        },
      ],
    });

    renderThreadList(<ThreadList messages={[msg]} />);

    const button = screen.getByRole('button', { name: /report\.pdf/i });
    button.click();

    expect(await screen.findByTitle('report.pdf')).toBeInTheDocument();
    expect(screen.getByText('Сохранить')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Открыть' })).toHaveAttribute(
      'href',
      '/api/messages/5/attachments/42/download',
    );
  });

  it('renders no attachment buttons when message has none', () => {
    const msg = makeMessage({ id: 6, attachments: [] });

    renderThreadList(<ThreadList messages={[msg]} />);

    expect(screen.queryByRole('button', { name: /Вложение/i })).not.toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('группирует сообщения по дням (AC1)', () => {
    const today = new Date().toISOString();
    const yesterday = new Date(Date.now() - 86400000).toISOString();
    const msgs = [
      makeMessage({ id: 1, content: 'Сегодняшнее', created_at: today }),
      makeMessage({ id: 2, content: 'Вчерашнее', created_at: yesterday }),
    ];

    renderThreadList(<ThreadList messages={msgs} />);

    expect(screen.getByText('Сегодня')).toBeInTheDocument();
    expect(screen.getByText('Вчера')).toBeInTheDocument();
    expect(screen.getByText('Сегодняшнее')).toBeInTheDocument();
    expect(screen.getByText('Вчерашнее')).toBeInTheDocument();
  });

  it('рендерит кликабельные ссылки из content_html (AC1/AC3)', () => {
    const msg = makeMessage({
      id: 9,
      content: 'Ссылка https://example.com',
      content_html: 'Ссылка <a href="https://example.com" target="_blank" rel="noopener noreferrer">https://example.com</a>',
    });

    renderThreadList(<ThreadList messages={[msg]} />);

    const link = screen.getByRole('link', { name: 'https://example.com' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('экранирует XSS в content_html (AC4)', () => {
    const msg = makeMessage({
      id: 10,
      content: '<script>alert(1)</script>',
      content_html: '&lt;script&gt;alert(1)&lt;/script&gt;',
    });

    renderThreadList(<ThreadList messages={[msg]} />);

    expect(screen.queryByRole('script')).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain('<script>alert(1)</script>');
  });
});
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import GlobalSearch from '../GlobalSearch';

function renderSearch(open = true, onClose = () => {}) {
  return render(
    <MemoryRouter>
      <GlobalSearch open={open} onClose={onClose} />
    </MemoryRouter>,
  );
}

const CONTACTS = [
  { id: 1, name: 'Иван Петров', phone: null, email: null, life_sphere: 'personal', is_known: true, is_favorite: false, telegram_id: null, telegram_username: null, notes: null, channel_types: [], folder_id: null, last_message_at: null, deleted_at: null, created_at: '2026-07-01T00:00:00', updated_at: '2026-07-01T00:00:00' },
];

const MESSAGES = [
  { id: 10, contact_id: 1, channel: 'telegram', channel_message_id: null, content: 'Привет, это тест', direction: 'incoming', status: 'unread', created_at: '2026-08-01T00:00:00', updated_at: '2026-08-01T00:00:00' },
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

describe('GlobalSearch', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('пустой запрос не шлёт запросы (AC4 negative)', async () => {
    const searchMessages = vi.fn();
    const searchContacts = vi.fn();
    server.use(
      http.get('/api/messages/search', () => { searchMessages(); return HttpResponse.json([]); }),
      http.get('/api/contacts', () => { searchContacts(); return HttpResponse.json([]); }),
    );
    renderSearch();
    const input = screen.getByPlaceholderText('Поиск по сообщениям и контактам...');
    fireEvent.change(input, { target: { value: '   ' } });
    await sleep(400);
    expect(searchMessages).not.toHaveBeenCalled();
    expect(searchContacts).not.toHaveBeenCalled();
  });

  it('поиск возвращает сообщения и контакты (AC2)', async () => {
    server.use(
      http.get('/api/messages/search', () => HttpResponse.json(MESSAGES)),
      http.get('/api/contacts', () => HttpResponse.json(CONTACTS)),
    );
    renderSearch();
    const input = screen.getByPlaceholderText('Поиск по сообщениям и контактам...');
    fireEvent.change(input, { target: { value: 'тест' } });

    expect(await screen.findByText('Иван Петров')).toBeInTheDocument();
    expect(screen.getByText('Привет, это тест')).toBeInTheDocument();
  });

  it('переход к диалогу и контакту (AC3)', async () => {
    server.use(
      http.get('/api/messages/search', () => HttpResponse.json(MESSAGES)),
      http.get('/api/contacts', () => HttpResponse.json(CONTACTS)),
    );
    const onClose = vi.fn();
    renderSearch(true, onClose);
    const input = screen.getByPlaceholderText('Поиск по сообщениям и контактам...');
    fireEvent.change(input, { target: { value: 'тест' } });

    const msg = await screen.findByText('Привет, это тест');
    fireEvent.click(msg);
    expect(onClose).toHaveBeenCalled();
  });

  it('закрывается по Escape (Ctrl+K)', async () => {
    const onClose = vi.fn();
    renderSearch(true, onClose);
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Поиск по сообщениям и контактам...')).toBeInTheDocument();
    });
  });
});

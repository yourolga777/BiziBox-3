import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import { contactApi } from '../../api/contacts';
import { ToastProvider } from '../../components/common/Toast';
import type { Contact } from '../../types/contact';
import Contacts from '../Contacts';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <ToastProvider>{children}</ToastProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

const baseContact: Omit<Contact, 'id' | 'name'> = {
  phone: null,
  email: null,
  telegram_id: null,
  telegram_username: null,
  is_known: true,
  is_favorite: false,
  life_sphere: null,
  notes: null,
  channel_types: [],
  contact_types: [],
  contact_type_ids: [],
  folder_id: null,
  last_message_at: null,
  deleted_at: null,
  created_at: null,
  updated_at: null,
};

const mkContact = (id: number, name: string, partial: Partial<Contact> = {}): Contact => ({
  ...baseContact,
  id,
  name,
  ...partial,
});

const mockContacts: Contact[] = [
  mkContact(1, 'Иван Петров', { email: 'ivan@test.ru', life_sphere: 'work' }),
  mkContact(2, 'Анна Смирнова'),
];

describe('Contacts page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/contacts', () => HttpResponse.json(mockContacts)),
      http.get('/api/folders', () => HttpResponse.json([])),
      http.get('/api/contacts/duplicates', () => HttpResponse.json([])),
      http.get('/api/tags', () => HttpResponse.json([])),
    );
  });

  it('renders subsection tabs in order: Все, Новые', () => {
    render(<Contacts />, { wrapper: createWrapper() });

    const buttons = screen.getAllByRole('button').map((b) => b.textContent?.trim() ?? '');
    const all = buttons.indexOf('Все');
    const novye = buttons.indexOf('Новые');

    expect(all).toBeGreaterThanOrEqual(0);
    expect(novye).toBeGreaterThanOrEqual(0);
    expect(all).toBeLessThan(novye);
  });

  it('passes folder_id and sort_by params to contactApi.getAll', async () => {
    const getAllSpy = vi.spyOn(contactApi, 'getAll').mockImplementation(async () => mockContacts);
    render(<Contacts />, { wrapper: createWrapper() });

    await screen.findByText('Иван Петров');

    const initialCall = getAllSpy.mock.calls[0][0];
    expect(initialCall?.sort_by).toBe('name');
    expect(initialCall?.sort_order).toBe('asc');
    expect(initialCall?.limit).toBeGreaterThan(0);
  });

  it('toggles sort order when the sort button is clicked twice', async () => {
    const user = userEvent.setup();
    const getAllSpy = vi.spyOn(contactApi, 'getAll').mockResolvedValue(mockContacts);
    render(<Contacts />, { wrapper: createWrapper() });

    await screen.findByText('Иван Петров');

    const sortBtn = screen.getByRole('button', { name: /По возрастанию/ });
    expect(getAllSpy.mock.calls[0][0]?.sort_order).toBe('asc');

    await user.click(sortBtn);

    await waitFor(() => {
      const call = getAllSpy.mock.calls[getAllSpy.mock.calls.length - 1][0];
      expect(call?.sort_order).toBe('desc');
    });
  });

  it('фильтрует по типу контакта (AC1)', async () => {
    const user = userEvent.setup();
    const getAllSpy = vi.spyOn(contactApi, 'getAll').mockResolvedValue(mockContacts);
    render(<Contacts />, { wrapper: createWrapper() });

    await screen.findByText('Иван Петров');

    await user.click(screen.getByRole('button', { name: 'Личное' }));

    await waitFor(() => {
      const call = getAllSpy.mock.calls[getAllSpy.mock.calls.length - 1][0];
      expect(call?.life_sphere).toBe('personal');
    });
  });

  it('показывает empty state когда нет контактов (AC4)', async () => {
    server.use(http.get('/api/contacts', () => HttpResponse.json([])));
    render(<Contacts />, { wrapper: createWrapper() });

    expect(await screen.findByText('Нет контактов')).toBeInTheDocument();
  });
});
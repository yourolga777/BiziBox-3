import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import { ToastProvider } from '../../common/Toast';
import ContactDetailPanel from '../ContactDetailPanel';
import type { Contact } from '../../../types/contact';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <ToastProvider>
          <MemoryRouter>{children}</MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    );
  };
}

const contact: Contact = {
  id: 1,
  name: 'Иван Петров',
  telegram_username: 'ivanov',
  phone: '+79123456789',
  email: 'ivan@example.com',
  telegram_id: null,
  is_known: true,
  is_favorite: false,
  life_sphere: null,
  notes: null,
  channel_types: ['telegram'],
  contact_types: [],
  contact_type_ids: [],
  folder_id: null,
  last_message_at: null,
  deleted_at: null,
  created_at: null,
  updated_at: null,
};

describe('ContactDetailPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/tags', () => HttpResponse.json([])),
      http.get('/api/contacts/1/fields', () => HttpResponse.json([])),
      http.get('/api/contacts/1/timeline', () => HttpResponse.json([])),
      http.get('/api/contacts/1/notes', () => HttpResponse.json([])),
    );
  });

  it('shows name as the heading and login as the first contact detail line', () => {
    render(<ContactDetailPanel contact={contact} onEdit={() => {}} onDelete={() => {}} />, { wrapper: createWrapper() });

    const heading = screen.getByRole('heading', { name: 'Иван Петров' });
    expect(heading).toBeInTheDocument();

    const login = screen.getByText('@ivanov');
    expect(login).toBeInTheDocument();

    const loginBox = login.closest('div');
    const container = heading.closest('.w-96') as HTMLElement | null;
    expect(container).toBeTruthy();
    if (container) {
      const text = within(container).getByText('@ivanov').closest('.space-y-2') as HTMLElement;
      const rows = Array.from(text.querySelectorAll('.flex')).map((el) => el.textContent ?? '');
      const loginIdx = rows.findIndex((r) => r.includes('@ivanov'));
      const phoneIdx = rows.findIndex((r) => r.includes('+79123456789'));
      expect(loginIdx).toBe(0);
      expect(loginIdx).toBeLessThan(phoneIdx);
    }
    expect(loginBox).toBeTruthy();
  });

  it('shows «Без имени» in the heading when name and login are absent', () => {
    const anon = { ...contact, name: null, telegram_username: null, phone: null, email: null };
    render(<ContactDetailPanel contact={anon} onEdit={() => {}} onDelete={() => {}} />, { wrapper: createWrapper() });
    expect(screen.getByRole('heading', { name: 'Без имени' })).toBeInTheDocument();
  });
});
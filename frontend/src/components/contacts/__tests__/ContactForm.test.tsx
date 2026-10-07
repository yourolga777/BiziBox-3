import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../../mocks/server';
import ContactForm from '../ContactForm';
import { contactSchema } from '../../../schemas';
import type { Contact } from '../../../types/contact';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const editContact: Contact = {
  id: 1,
  name: 'Иван Петров',
  phone: '+79161234567',
  email: 'ivan@example.com',
  telegram_id: null,
  telegram_username: '@ivan',
  is_known: false,
  is_favorite: false,
  life_sphere: 'personal',
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

describe('ContactForm', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/folders', () =>
        HttpResponse.json([
          { id: 10, name: 'Заказы', category_key: 'order', color: null, sort_order: 0, is_default: false, sphere: 'personal', parent_id: null, created_at: null },
        ]),
      ),
      http.get('/api/contacts', () =>
        HttpResponse.json([
          { ...editContact, id: 2, name: 'Анна Смирнова', telegram_username: null, phone: '+79990001122' },
        ]),
      ),
    );
  });

  it('shows folder tree and merge section when editing', async () => {
    render(<ContactForm initial={editContact} onSubmit={vi.fn()} onCancel={vi.fn()} onMerge={vi.fn()} />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText('Заказы')).toBeTruthy());
    expect(screen.getByText('Объединить с контактом')).toBeTruthy();
  });

  it('does not show merge section when creating', () => {
    render(<ContactForm initial={null} onSubmit={vi.fn()} onCancel={vi.fn()} />, { wrapper: createWrapper() });

    expect(screen.queryByText('Объединить с контактом')).toBeNull();
  });

  it('searches and merges a contact', async () => {
    const onMerge = vi.fn().mockResolvedValue(undefined);
    render(<ContactForm initial={editContact} onSubmit={vi.fn()} onCancel={vi.fn()} onMerge={onMerge} />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText('Объединить с контактом')).toBeTruthy());
    await userEvent.click(screen.getByText('Объединить с контактом'));

    const input = screen.getByPlaceholderText('Поиск контакта для объединения...');
    await userEvent.type(input, 'Анна');
    await waitFor(() => expect(screen.getByText('Анна Смирнова')).toBeTruthy());

    await userEvent.click(screen.getByText('Анна Смирнова'));
    await waitFor(() => expect(onMerge).toHaveBeenCalledWith(2));
  });

  it('submits form data on save', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ContactForm initial={editContact} onSubmit={onSubmit} onCancel={vi.fn()} onMerge={vi.fn()} />, { wrapper: createWrapper() });

    const nameInput = screen.getByLabelText('Имя') as HTMLInputElement;
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Новое Имя');
    await userEvent.click(screen.getByText('Сохранить'));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const submitted = onSubmit.mock.calls[0][0] as Record<string, unknown>;
    expect(submitted.name).toBe('Новое Имя');
  });

  it('submits numeric folder_ids when a folder is selected', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ContactForm initial={editContact} onSubmit={onSubmit} onCancel={vi.fn()} onMerge={vi.fn()} />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText('Заказы')).toBeTruthy());
    await userEvent.click(screen.getByText('Заказы'));
    await userEvent.click(screen.getByText('Сохранить'));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const submitted = onSubmit.mock.calls[0][0] as Record<string, unknown>;
    expect(submitted.folder_ids).toEqual([10]);
  });

  it('does not save and shows error when creating with empty name/phone/email', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ContactForm initial={null} onSubmit={onSubmit} onCancel={vi.fn()} />, { wrapper: createWrapper() });

    await userEvent.click(screen.getByText('Сохранить'));

    await waitFor(() => expect(screen.getByText('Укажите хотя бы имя, телефон или email')).toBeTruthy());
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows favorite checkbox', async () => {
    render(<ContactForm initial={editContact} onSubmit={vi.fn()} onCancel={vi.fn()} onMerge={vi.fn()} />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByLabelText('Избранное')).toBeTruthy());
  });

  it('валидирует некорректную дату рождения (AC3)', () => {
    const invalid = contactSchema.safeParse({ birthday: 'not-a-date' });
    expect(invalid.success).toBe(false);

    const futureOk = contactSchema.safeParse({ birthday: '1990-05-15' });
    expect(futureOk.success).toBe(true);
  });

  it('предупреждает о несохранённых изменениях при отмене (AC4)', async () => {
    const onCancel = vi.fn();
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<ContactForm initial={editContact} onSubmit={vi.fn()} onCancel={onCancel} onMerge={vi.fn()} />, { wrapper: createWrapper() });

    const nameInput = screen.getByLabelText('Имя');
    fireEvent.change(nameInput, { target: { value: 'Изменённое имя' } });
    fireEvent.click(screen.getByText('Отмена'));

    expect(confirmSpy).toHaveBeenCalled();
    expect(onCancel).not.toHaveBeenCalled();
  });
});

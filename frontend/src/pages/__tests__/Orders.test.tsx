import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import { ToastProvider } from '../../components/common/Toast';
import Orders from '../Orders';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/orders']}>{children}</MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    );
  };
}

const orderNew = {
  id: 1,
  order_number: 'ORD-20260924-1001',
  contact_id: 1,
  contact_name: 'Иван Петров',
  message_id: null,
  status: 'new',
  total: 500,
  delivery_address: 'ул. Ленина, 5',
  payment_method: 'card',
  paid: false,
  items: [
    { id: 11, order_id: 1, product_id: null, name: 'Пицца Маргарита', quantity: 1, price: 500, created_at: '2026-09-24T10:00:00' },
  ],
  comments: [],
  deleted_at: null,
  created_at: '2026-09-24T10:00:00',
  updated_at: '2026-09-24T10:00:00',
};

const orderCompleted = {
  id: 2,
  order_number: 'ORD-20260922-1002',
  contact_id: 2,
  contact_name: 'Анна Смирнова',
  message_id: null,
  status: 'completed',
  total: 1200,
  delivery_address: null,
  payment_method: null,
  paid: true,
  items: [],
  comments: [],
  deleted_at: null,
  created_at: '2026-09-22T09:00:00',
  updated_at: '2026-09-23T12:00:00',
};

describe('Orders page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/orders', () =>
        HttpResponse.json([orderNew, orderCompleted]),
      ),
      http.get('/api/orders/1', () =>
        HttpResponse.json({
          ...orderNew,
          comments: [
            { id: 31, order_id: 1, content: 'Позвонить перед доставкой', created_at: '2026-09-24T11:00:00' },
          ],
        }),
      ),
      http.get('/api/contacts', () =>
        HttpResponse.json([
          { id: 1, name: 'Иван Петров', phone: null, email: null, telegram_id: null, telegram_username: null, is_known: false, is_favorite: false, life_sphere: null, notes: null, channel_types: [], folder_id: null, last_message_at: null, deleted_at: null, created_at: null, updated_at: null },
          { id: 2, name: 'Анна Смирнова', phone: null, email: null, telegram_id: null, telegram_username: null, is_known: false, is_favorite: false, life_sphere: null, notes: null, channel_types: [], folder_id: null, last_message_at: null, deleted_at: null, created_at: null, updated_at: null },
        ]),
      ),
    );
  });

  it('renders orders loaded via useOrdersQuery and aggregate counts', async () => {
    render(<Orders />, { wrapper: createWrapper() });

    await screen.findByText('ORD-20260924-1001');
    expect(screen.getByText('ORD-20260922-1002')).toBeInTheDocument();

    expect(screen.getByText('Всего').nextElementSibling?.textContent).toBe('2');
    expect(screen.getByText('Новых').nextElementSibling?.textContent).toBe('1');
    expect(screen.getAllByText('В работе')[0].nextElementSibling?.textContent).toBe('0');
    expect(screen.getByText('Отправлено').nextElementSibling?.textContent).toBe('0');
    expect(screen.getByText('Сумма активных').nextElementSibling?.textContent?.replace(/\s/g, ' ')).toBe('1 700 ₽');
  });

  it('renders kanban columns with correct status labels', async () => {
    render(<Orders />, { wrapper: createWrapper() });

    await screen.findByText('ORD-20260924-1001');

    expect(screen.getByRole('heading', { name: 'Новый' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'В работе' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Отправлен' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Завершён' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Отменён' })).toBeInTheDocument();

    expect(screen.getByRole('button', { name: /ORD-20260924-1001/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ORD-20260922-1002/ })).toBeInTheDocument();
  });

  it('imports orders from CSV and shows the result', async () => {
    server.use(
      http.post('/api/orders/import/csv', () =>
        HttpResponse.json({ created: 1, skipped: 0, errors: [] }),
      ),
    );
    render(<Orders />, { wrapper: createWrapper() });
    await screen.findByText('ORD-20260924-1001');

    await userEvent.click(screen.getByRole('button', { name: /Импорт/ }));
    expect(await screen.findByText('Импорт заказов из CSV')).toBeInTheDocument();

    const file = new File(['dummy'], 'orders.csv', { type: 'text/csv' });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByRole('button', { name: 'Импортировать' }));

    expect(await screen.findByText(/Импорт завершён: создано 1, пропущено 0/)).toBeInTheDocument();
  });

  it('opens order detail modal on card click', async () => {
    render(<Orders />, { wrapper: createWrapper() });
    await screen.findByText('ORD-20260924-1001');

    const card = screen.getByRole('button', { name: /ORD-20260924-1001/ });
    await userEvent.click(card);

    expect(await screen.findByText('Пицца Маргарита')).toBeInTheDocument();
    expect(screen.getByText('Позвонить перед доставкой')).toBeInTheDocument();
    expect(screen.getByText('Адрес доставки')).toBeInTheDocument();
  });

  it('creates an order from the create modal', async () => {
    server.use(
      http.post('/api/orders', () =>
        HttpResponse.json({
          ...orderNew,
          id: 3,
          order_number: 'ORD-20260924-1003',
          created_at: '2026-09-24T12:00:00',
          updated_at: '2026-09-24T12:00:00',
        }, { status: 201 }),
      ),
    );
    render(<Orders />, { wrapper: createWrapper() });
    await screen.findByText('ORD-20260924-1001');

    await userEvent.click(screen.getByRole('button', { name: /Создать/ }));
    expect(await screen.findByText('Новый заказ')).toBeInTheDocument();

    await userEvent.type(screen.getByPlaceholderText('Имя *'), 'Новый клиент');
    await userEvent.type(screen.getByPlaceholderText('Товар *'), 'Сыр');
    await userEvent.type(screen.getByPlaceholderText('Цена'), '300');

    await userEvent.click(screen.getByRole('button', { name: 'Создать заказ' }));

    expect((await screen.findAllByText(/Заказ создан/)).length).toBeGreaterThan(0);
  });
});
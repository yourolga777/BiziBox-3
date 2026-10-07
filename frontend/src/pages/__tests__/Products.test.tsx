import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import { ToastProvider } from '../../components/common/Toast';
import type { Product } from '../../types/product';
import Products from '../Products';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/products']}>{children}</MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    );
  };
}

const product1 = {
  id: 1,
  owner_id: 1,
  name: 'Стул офисный',
  sku: 'CH-001',
  price: 4500,
  purchase_price: 3000,
  stock: 20,
  unit: 'шт',
  description: 'Удобный стул',
  supplier_id: 1,
  supplier_name: 'ООО Мебель',
  deleted_at: null,
  created_at: '2026-09-25T10:00:00',
  updated_at: '2026-09-25T10:00:00',
  margin: 1500,
  margin_percent: 50,
};

const product2 = {
  id: 2,
  owner_id: 1,
  name: 'Стол обеденный',
  sku: 'TB-002',
  price: 8000,
  purchase_price: 5000,
  stock: 5,
  unit: 'шт',
  description: null,
  supplier_id: null,
  supplier_name: null,
  deleted_at: null,
  created_at: '2026-09-24T09:00:00',
  updated_at: '2026-09-24T09:00:00',
  margin: 3000,
  margin_percent: 60,
};

const supplier1 = {
  id: 1,
  owner_id: 1,
  contact_id: 1,
  contact_name: 'ООО Мебель',
  contact_phone: null,
  company_name: 'ООО Мебель',
  inn: '1234567890',
  notes: null,
  deleted_at: null,
  created_at: '2026-09-25T10:00:00',
  updated_at: '2026-09-25T10:00:00',
};

const contacts = [
  { id: 1, name: 'ООО Мебель', phone: null, email: null, telegram_id: null, telegram_username: null, is_known: false, is_favorite: false, life_sphere: null, notes: null, channel_types: [], folder_id: null, last_message_at: null, deleted_at: null, created_at: null, updated_at: null },
  { id: 2, name: 'Иван Петров', phone: null, email: null, telegram_id: null, telegram_username: null, is_known: false, is_favorite: false, life_sphere: null, notes: null, channel_types: [], folder_id: null, last_message_at: null, deleted_at: null, created_at: null, updated_at: null },
];

describe('Products page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    server.resetHandlers();
    server.use(
      http.get('/api/products', () => HttpResponse.json([product1, product2])),
      http.get('/api/suppliers', () => HttpResponse.json([supplier1])),
      http.get('/api/contacts', () => HttpResponse.json(contacts)),
    );
  });

  it('renders products table with names and prices', async () => {
    render(<Products />, { wrapper: createWrapper() });

    expect(await screen.findByText('Стул офисный')).toBeInTheDocument();
    expect(screen.getByText('Стол обеденный')).toBeInTheDocument();
    expect(screen.getByText('CH-001')).toBeInTheDocument();
    expect(screen.getAllByText('ООО Мебель').length).toBeGreaterThanOrEqual(1);
  });

  it('opens product form on create button', async () => {
    render(<Products />, { wrapper: createWrapper() });
    await screen.findByText('Стул офисный');

    await userEvent.click(screen.getByRole('button', { name: /Товар/ }));

    expect(await screen.findByText('Новый товар')).toBeInTheDocument();
    expect(screen.getByLabelText('Название *')).toBeInTheDocument();
  });

  it('shows imported products without page reload', async () => {
    let products: Product[] = [];
    const imported: Product = {
      ...product1,
      id: 9,
      name: 'Тумба импортная',
      sku: 'IM-900',
      supplier_name: 'ООО СветТех',
    };
    const csvFile = new File(['name,sku\nТумба импортная,IM-900\n'], 'katalog.csv', { type: 'text/csv' });
    server.use(
      http.get('/api/products', () => HttpResponse.json(products)),
      http.post('/api/products/import', async () => {
        products = [imported];
        return HttpResponse.json({ created: 1, updated: 0, skipped: 0 });
      }),
    );
    render(<Products />, { wrapper: createWrapper() });

    await screen.findByText(/Товаров пока нет/);

    await userEvent.click(screen.getByRole('button', { name: /Импорт/ }));
    await screen.findByText('Импорт товаров из CSV');

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(fileInput, csvFile);
    await userEvent.click(screen.getByRole('button', { name: 'Импортировать' }));

    expect(await screen.findByText('Импорт завершён: создано 1, обновлено 0, пропущено 0.')).toBeInTheDocument();
    expect(await screen.findByText('Тумба импортная')).toBeInTheDocument();
    expect(screen.queryByText(/Товаров пока нет/)).not.toBeInTheDocument();
  });

  it('creates a product from the form', async () => {
    const list: Product[] = [product1, product2];
    server.use(
      http.get('/api/products', () => HttpResponse.json(list)),
      http.post('/api/products', async ({ request }) => {
        const body = await request.json() as Record<string, unknown>;
        const created: Product = {
          ...product1,
          id: 3,
          name: String(body.name ?? 'Тестовый стул'),
          sku: typeof body.sku === 'string' ? body.sku : null,
          price: typeof body.price === 'number' ? body.price : null,
          purchase_price: typeof body.purchase_price === 'number' ? body.purchase_price : null,
          stock: typeof body.stock === 'number' ? body.stock : null,
          unit: typeof body.unit === 'string' ? body.unit : 'шт',
          description: typeof body.description === 'string' ? body.description : null,
          supplier_id: typeof body.supplier_id === 'number' ? body.supplier_id : null,
          supplier_name: null,
          margin: 0,
          margin_percent: null,
        };
        list.push(created);
        return HttpResponse.json(created, { status: 201 });
      }),
    );
    render(<Products />, { wrapper: createWrapper() });
    await screen.findByText('Стул офисный');

    await userEvent.click(screen.getByRole('button', { name: /Товар/ }));
    await screen.findByText('Новый товар');

    await userEvent.type(screen.getByLabelText('Название *'), 'Тестовый стул');

    await userEvent.click(screen.getByRole('button', { name: 'Сохранить' }));

    expect(await screen.findByText('Тестовый стул')).toBeInTheDocument();
  });

  it('opens supplier manager modal', async () => {
    render(<Products />, { wrapper: createWrapper() });
    await screen.findByText('Стул офисный');

    await userEvent.click(screen.getByRole('button', { name: /Поставщики/ }));

    expect(await screen.findByText('Добавить поставщика')).toBeInTheDocument();
  });
});

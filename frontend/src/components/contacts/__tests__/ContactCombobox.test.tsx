import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ContactCombobox from '../ContactCombobox';
import type { Contact } from '../../../types/contact';

function makeContact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: 1,
    name: null,
    phone: null,
    email: null,
    telegram_id: null,
    telegram_username: null,
    is_known: false,
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
    ...overrides,
  };
}

const CONTACTS = [
  makeContact({ id: 1, name: 'Иван Петров', phone: '+79161234567', email: 'ivan@example.com' }),
  makeContact({ id: 2, name: 'Мария Сидорова', phone: '+79269876543' }),
  makeContact({ id: 3, name: null, telegram_username: 'alex_dev' }),
];

describe('ContactCombobox', () => {
  it('показывает все контакты при пустом поиске', () => {
    render(<ContactCombobox contacts={CONTACTS} value={null} onChange={() => {}} />);
    fireEvent.focus(screen.getByPlaceholderText('Поиск контакта...'));
    expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
    expect(screen.getByText('@alex_dev')).toBeInTheDocument();
  });

  it('фильтрует по имени', () => {
    render(<ContactCombobox contacts={CONTACTS} value={null} onChange={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText('Поиск контакта...'), { target: { value: 'мария' } });
    expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
    expect(screen.queryByText('Иван Петров')).not.toBeInTheDocument();
  });

  it('фильтрует по телефону и email', () => {
    render(<ContactCombobox contacts={CONTACTS} value={null} onChange={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText('Поиск контакта...'), { target: { value: '7926' } });
    expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
    expect(screen.queryByText('Иван Петров')).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Поиск контакта...'), { target: { value: 'ivan@' } });
    expect(screen.getByText('Иван Петров')).toBeInTheDocument();
  });

  it('отображает выбранный контакт чипсом и сбрасывает', () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <ContactCombobox contacts={CONTACTS} value={1} onChange={onChange} />,
    );
    expect(screen.getByText('Иван Петров')).toBeInTheDocument();

    fireEvent.click(screen.getByTitle('Сбросить'));
    expect(onChange).toHaveBeenCalledWith(null);
    rerender(<ContactCombobox contacts={CONTACTS} value={null} onChange={onChange} />);
    expect(screen.getByPlaceholderText('Поиск контакта...')).toBeInTheDocument();
  });

  it('вызывает onChange при выборе контакта', () => {
    const onChange = vi.fn();
    render(<ContactCombobox contacts={CONTACTS} value={null} onChange={onChange} />);
    fireEvent.focus(screen.getByPlaceholderText('Поиск контакта...'));
    fireEvent.click(screen.getByText('Мария Сидорова'));
    expect(onChange).toHaveBeenCalledWith(2);
  });

  it('исключает контакты из excludeIds', () => {
    render(
      <ContactCombobox contacts={CONTACTS} value={null} onChange={() => {}} excludeIds={[1]} />,
    );
    fireEvent.focus(screen.getByPlaceholderText('Поиск контакта...'));
    expect(screen.queryByText('Иван Петров')).not.toBeInTheDocument();
    expect(screen.getByText('Мария Сидорова')).toBeInTheDocument();
  });
});

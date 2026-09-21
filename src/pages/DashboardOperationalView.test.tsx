import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';

const mockFetchWithAuth = vi.fn();

vi.mock('../services/api', () => ({
  API_BASE: 'http://localhost:8000/api/v1',
  fetchWithAuth: (...args: any[]) => mockFetchWithAuth(...args),
}));

import DashboardOperationalView from './DashboardOperationalView';

describe('DashboardOperationalView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('autonomously fetches orders and calculates operational KPIs and order queue', async () => {
    const todayISO = new Date().toISOString();
    const fakeOrders = [
      {
        id: 'ord-12345678',
        customerName: 'Maria Silva',
        total_amount: 150.00,
        status: 'completed',
        createdAt: todayISO,
      },
      {
        id: 'ord-87654321',
        customerName: 'João Santos',
        total: 50.00,
        status: 'pending',
        createdAt: todayISO,
      },
    ];

    mockFetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ orders: fakeOrders }),
    });

    render(<DashboardOperationalView />);

    // Check fetch was called with /orders endpoint
    await waitFor(() => {
      expect(mockFetchWithAuth).toHaveBeenCalledWith(
        expect.stringContaining('/orders')
      );
    });

    // Check KPI calculations:
    // 2 orders today in Pedidos Hoje card
    await waitFor(() => {
      const pedidosHojeCard = screen.getByText('Pedidos Hoje').closest('.surface-card');
      expect(pedidosHojeCard).toHaveTextContent('2');
    });

    // Faturamento: 150 + 50 = R$ 200,00
    expect(screen.getByText('R$ 200,00')).toBeInTheDocument();

    // Ticket Médio: 200 / 2 = R$ 100,00
    expect(screen.getByText('R$ 100,00')).toBeInTheDocument();

    // Conversão: 1 completed out of 2 = 50.0%
    expect(screen.getByText('50.0%')).toBeInTheDocument();

    // Check Orders Queue Table
    expect(screen.getByText('Maria Silva')).toBeInTheDocument();
    expect(screen.getByText('João Santos')).toBeInTheDocument();
    expect(screen.getByText('Concluído')).toBeInTheDocument();
    expect(screen.getByText('Novo Pedido')).toBeInTheDocument();
  });

  it('renders empty queue state when API returns no orders', async () => {
    mockFetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ orders: [] }),
    });

    render(<DashboardOperationalView />);

    await waitFor(() => {
      expect(mockFetchWithAuth).toHaveBeenCalled();
    });

    expect(await screen.findByText('Nenhum pedido mapeado na sessão atual.')).toBeInTheDocument();
  });

  it('re-fetches orders when refresh button is clicked', async () => {
    mockFetchWithAuth.mockResolvedValue({
      ok: true,
      json: async () => ({ orders: [] }),
    });

    const onRefreshMock = vi.fn();
    render(<DashboardOperationalView onRefresh={onRefreshMock} />);

    await waitFor(() => {
      expect(mockFetchWithAuth).toHaveBeenCalledTimes(1);
    });

    const refreshBtn = screen.getByTitle('Atualizar Dados Operacionais');
    await act(async () => {
      fireEvent.click(refreshBtn);
    });

    expect(onRefreshMock).toHaveBeenCalledTimes(1);
    expect(mockFetchWithAuth).toHaveBeenCalledTimes(2);
  });
});

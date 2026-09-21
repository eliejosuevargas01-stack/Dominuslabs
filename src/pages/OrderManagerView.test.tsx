import '@testing-library/jest-dom';
import { act, render, screen, fireEvent } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { toastError, MockSSEClient } = vi.hoisted(() => {
  class MockSSEClient {
    static instances: MockSSEClient[] = [];

    url: string;
    onMessage: (data: any, event?: string) => void;
    onOpen?: () => void;
    onError?: (error: any) => void;
    onClose?: () => void;
    isClosed = false;

    constructor(options: {
      url: string;
      onMessage: (data: any, event?: string) => void;
      onOpen?: () => void;
      onError?: (error: any) => void;
      onClose?: () => void;
    }) {
      this.url = options.url;
      this.onMessage = options.onMessage;
      this.onOpen = options.onOpen;
      this.onError = options.onError;
      this.onClose = options.onClose;
      MockSSEClient.instances.push(this);
    }

    async connect(): Promise<void> {
      this.isClosed = false;
    }

    disconnect(): void {
      this.isClosed = true;
      this.onClose?.();
    }

    open(): void {
      this.onOpen?.();
    }

    message(data: unknown, event?: string): void {
      this.onMessage(data, event);
    }
  }

  return { toastError: vi.fn(), MockSSEClient };
});

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: toastError } }));
vi.mock('../services/sseClient', () => ({
  SSEClient: MockSSEClient,
}));

import OrderManagerView from './OrderManagerView';

const pendingOrder = {
  id: 'pedido-pendente',
  customerName: 'Cliente',
  total: 74.97,
  address: 'Rua A, 10',
  items: [{ name: 'Brownie', quantity: 1 }],
  status: 'pending' as const,
  createdAt: '2026-08-31T14:48:07.915Z',
};

describe('OrderManagerView', () => {
  beforeEach(() => {
    MockSSEClient.instances = [];
    localStorage.setItem('admin_token', 'fake_token');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ orders: [] }),
    }));
    toastError.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('connects to the authenticated Order Manager SSE', async () => {
    await act(async () => { render(<OrderManagerView />); });

    expect(MockSSEClient.instances).toHaveLength(1);
    expect(MockSSEClient.instances[0].url).toEqual(expect.stringContaining('/api/v1/orders/events'));

    act(() => MockSSEClient.instances[0].open());
    expect(screen.getAllByText('Conectado (Ao Vivo)')[0]).toBeInTheDocument();
  });

  it('renders new orders and applies updates received from another screen', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];
    const order = {
      id: 'pedido-123',
      customerName: 'Cliente',
      total: 74.97,
      address: 'Rua A, 10',
      items: [{ name: 'Brownie', quantity: 1 }],
      status: 'accepted' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => sse.message({ event: 'new_order', order }));
    expect(screen.getAllByText('#PEDIDO')[0]).toBeInTheDocument();
    
    const acceptedBadge = screen.getAllByText('Aceito')[0];
    expect(acceptedBadge).toBeInTheDocument();
    expect(acceptedBadge).toHaveClass('bg-blue-50', 'text-blue-700', 'border-blue-200');

    // Monetary formatting check
    expect(screen.getByText('R$ 74,97')).toBeInTheDocument();

    const wazeLink = screen.getByRole('link', { name: /abrir no waze/i });
    const wazeUrl = new URL(wazeLink.getAttribute('href')!);
    expect(wazeUrl.origin).toBe('https://waze.com');
    expect(wazeUrl.pathname).toBe('/ul');
    expect(wazeUrl.searchParams.get('q')).toBe('Rua A, 10');
    expect(wazeUrl.searchParams.get('navigate')).toBe('yes');
    expect(wazeUrl.searchParams.get('utm_source')).toBe('dominuslabs_order_manager');

    act(() => sse.message({ event: 'order_updated', order: { ...order, status: 'delivered' } }));
    
    // In active tab, bottom drawer shows shift summary
    expect(screen.getByText(/1 pedido concluído/i)).toBeInTheDocument();

    // Switch to history tab to inspect finalized order
    const historyTabBtn = screen.getByRole('button', { name: /Histórico & Finalizados/i });
    act(() => { historyTabBtn.click(); });

    const deliveredBadge = screen.getAllByText('Entregue')[0];
    expect(deliveredBadge).toBeInTheDocument();
    expect(deliveredBadge).toHaveClass('bg-emerald-50', 'text-emerald-700', 'border-emerald-200');
  });

  it('renders order with total_amount formatted as BRL currency and semantic pending badge', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];
    const orderWithTotalAmount = {
      id: 'pedido-valor-total',
      customerName: 'Cliente Teste',
      total: 50.00,
      total_amount: 129.90,
      address: 'Av Paulista, 1000',
      items: [{ name: 'Combo Premium', quantity: 2 }],
      status: 'pending' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => sse.message({ event: 'new_order', order: orderWithTotalAmount }));

    const pendingBadge = screen.getAllByText('Pendente')[0];
    expect(pendingBadge).toBeInTheDocument();
    expect(pendingBadge).toHaveClass('bg-amber-50', 'text-amber-700', 'border-amber-200');

    // Prioritizes total_amount over total
    expect(screen.getByText('R$ 129,90')).toBeInTheDocument();
  });

  it('applies semantic badge style for cancelled/rejected status in history tab', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];
    const rejectedOrder = {
      id: 'pedido-recusado',
      customerName: 'Cliente Recusa',
      total: 35.50,
      address: 'Rua B, 20',
      items: [{ name: 'Item', quantity: 1 }],
      status: 'rejected' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => sse.message({ event: 'new_order', order: rejectedOrder }));

    // Bottom drawer in active tab reflects rejected count
    expect(screen.getByText(/1 cancelados\/recusados/i)).toBeInTheDocument();

    // Switch to history tab to view card and badge
    const historyTabBtn = screen.getByRole('button', { name: /Histórico & Finalizados/i });
    act(() => { historyTabBtn.click(); });

    const rejectedBadge = screen.getAllByText('Recusado')[0];
    expect(rejectedBadge).toBeInTheDocument();
    expect(rejectedBadge).toHaveClass('bg-rose-50', 'text-rose-700', 'border-rose-200');
    expect(screen.getByText('R$ 35,50')).toBeInTheDocument();
  });

  it('separates incoming/pending orders into Novos & Entrantes and in-progress into Em Preparo & Rota', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];

    const pending = {
      id: 'ped-novo-01',
      customerName: 'Cliente Novo',
      total: 45.00,
      address: 'Rua das Flores, 100',
      items: [{ name: 'Pizza', quantity: 1 }],
      status: 'pending' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    const inPrep = {
      id: 'ped-prep-02',
      customerName: 'Cliente Preparo',
      total: 80.00,
      address: 'Av Brasil, 500',
      items: [{ name: 'Hambúrguer', quantity: 2 }],
      status: 'accepted' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => {
      sse.message({ event: 'new_order', order: pending });
      sse.message({ event: 'new_order', order: inPrep });
    });

    // Check column headers
    expect(screen.getByText('Novos & Entrantes')).toBeInTheDocument();
    expect(screen.getByText('Em Preparo & Rota')).toBeInTheDocument();

    // Pending order has "Novo" badge and appears in Novos & Entrantes
    expect(screen.getByText('Cliente Novo')).toBeInTheDocument();
    expect(screen.getByText('Novo')).toBeInTheDocument();

    // Accepted order appears in Em Preparo & Rota without "Novo" badge
    expect(screen.getByText('Cliente Preparo')).toBeInTheDocument();
  });

  it('switches to Histórico & Finalizados tab and displays closing metrics', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];

    const deliveredOrder = {
      id: 'ped-deliv-01',
      customerName: 'Cliente Entregue',
      total: 100.00,
      address: 'Rua C, 30',
      items: [{ name: 'Sushi', quantity: 1 }],
      status: 'delivered' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    const cancelledOrder = {
      id: 'ped-canc-02',
      customerName: 'Cliente Cancelado',
      total: 40.00,
      address: 'Rua D, 40',
      items: [{ name: 'Bebida', quantity: 2 }],
      status: 'cancelled' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => {
      sse.message({ event: 'new_order', order: deliveredOrder });
      sse.message({ event: 'new_order', order: cancelledOrder });
    });

    // Switch to history tab
    const historyTabBtn = screen.getByRole('button', { name: /Histórico & Finalizados/i });
    act(() => { historyTabBtn.click(); });

    // Closing metrics cards
    expect(screen.getByText('Pedidos Concluídos')).toBeInTheDocument();
    expect(screen.getByText('Cancelados / Recusados')).toBeInTheDocument();
    expect(screen.getByText('Faturamento Consolidado')).toBeInTheDocument();

    // Delivered count: 1
    expect(screen.getByText('Entregas realizadas com sucesso')).toBeInTheDocument();

    // Faturamento: R$ 100,00
    expect(screen.getByText('R$ 100,00')).toBeInTheDocument();
  });

  it('filters finalized orders by customer name or ID in history tab', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];

    const orderA = {
      id: 'ped-alpha-01',
      customerName: 'Alice Silva',
      total: 50.00,
      address: 'Rua 1',
      items: [{ name: 'Item A', quantity: 1 }],
      status: 'delivered' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    const orderB = {
      id: 'ped-beta-02',
      customerName: 'Bob Santos',
      total: 60.00,
      address: 'Rua 2',
      items: [{ name: 'Item B', quantity: 1 }],
      status: 'completed' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => {
      sse.message({ event: 'new_order', order: orderA });
      sse.message({ event: 'new_order', order: orderB });
    });

    // Switch to history tab
    act(() => { screen.getByRole('button', { name: /Histórico & Finalizados/i }).click(); });

    expect(screen.getByText('Alice Silva')).toBeInTheDocument();
    expect(screen.getByText('Bob Santos')).toBeInTheDocument();

    // Filter by "Alice"
    const searchInput = screen.getByPlaceholderText('Buscar por cliente, ID ou endereço...');
    act(() => {
      fireEvent.change(searchInput, { target: { value: 'Alice' } });
    });

    expect(screen.getByText('Alice Silva')).toBeInTheDocument();
    expect(screen.queryByText('Bob Santos')).not.toBeInTheDocument();

    // Filter by ID "PED-BE"
    act(() => {
      fireEvent.change(searchInput, { target: { value: 'PED-BE' } });
    });

    expect(screen.queryByText('Alice Silva')).not.toBeInTheDocument();
    expect(screen.getByText('Bob Santos')).toBeInTheDocument();
  });

  it('displays the correct summary in the minimized footer drawer on active tab and switches to history', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];

    const finishedOrder = {
      id: 'ped-concluido-99',
      customerName: 'Cliente Turno',
      total: 85.50,
      address: 'Rua Central, 50',
      items: [{ name: 'Combo', quantity: 1 }],
      status: 'delivered' as const,
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => { sse.message({ event: 'new_order', order: finishedOrder }); });

    // Check drawer summary in active tab
    expect(screen.getByText('Resumo do Turno: 1 pedido concluído')).toBeInTheDocument();
    expect(screen.getByText('R$ 85,50')).toBeInTheDocument();

    // Click "Ver Histórico Completo" in drawer
    const viewHistoryBtn = screen.getByRole('button', { name: /Ver Histórico Completo/i });
    act(() => { viewHistoryBtn.click(); });

    // Now history tab is active and tabpanel is visible
    expect(screen.getByRole('tabpanel', { name: /Histórico & Finalizados/i })).toBeInTheDocument();
  });

  it('closes the SSE connection when the screen is unmounted', async () => {
    let unmount: any;
    await act(async () => { unmount = render(<OrderManagerView />).unmount; });
    const sse = MockSSEClient.instances[0];

    unmount();

    expect(sse.isClosed).toBe(true);
  });

  it('ignores ping events without treating it as an order event', async () => {
    await act(async () => { render(<OrderManagerView />); });
    const sse = MockSSEClient.instances[0];

    act(() => sse.message({ event: 'ping' }));

    expect(screen.getByText('Nenhum pedido novo no momento')).toBeInTheDocument();
    expect(screen.getByText('Nenhum pedido em preparo ou rota')).toBeInTheDocument();
  });

  it('polling brings pending orders even before SSE connects', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ orders: [{ ...pendingOrder, id: 'pedido-poll' }] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<OrderManagerView />); });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('allows rejecting a pending order', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ orders: [pendingOrder] }),
    }).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ order: { ...pendingOrder, status: 'cancelled' } }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<OrderManagerView />); });

    const rejectBtn = screen.getByText('Recusar');
    await act(async () => { rejectBtn.click(); });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toContain('/reject');
    expect(toastError).not.toHaveBeenCalled();
  });

  it('cleans up polling interval on unmount', async () => {
    vi.spyOn(global, 'clearInterval');
    let unmount: any;
    await act(async () => { unmount = render(<OrderManagerView />).unmount; });

    unmount();

    expect(global.clearInterval).toHaveBeenCalled();
  });
});

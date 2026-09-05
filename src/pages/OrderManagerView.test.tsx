import '@testing-library/jest-dom';
import { act, render, screen, waitFor } from '@testing-library/react';
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
      status: 'accepted',
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => sse.message({ event: 'new_order', order }));
    expect(screen.getAllByText('Pedido #PEDIDO')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Aceito')[0]).toBeInTheDocument();
    const wazeUrl = new URL(screen.getAllByText('Abrir no Waze')[0].getAttribute('href')!);
    expect(wazeUrl.origin).toBe('https://waze.com');
    expect(wazeUrl.pathname).toBe('/ul');
    expect(wazeUrl.searchParams.get('q')).toBe('Rua A, 10');
    expect(wazeUrl.searchParams.get('navigate')).toBe('yes');
    expect(wazeUrl.searchParams.get('utm_source')).toBe('dominuslabs_order_manager');

    act(() => sse.message({ event: 'order_updated', order: { ...order, status: 'delivered' } }));
    expect(screen.getAllByText('Entregue')[0]).toBeInTheDocument();
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

    expect(screen.getAllByText('Nenhum pedido no momento.')[0]).toBeInTheDocument();
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

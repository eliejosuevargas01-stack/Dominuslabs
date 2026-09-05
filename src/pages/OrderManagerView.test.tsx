import { fetchEventSource } from '@microsoft/fetch-event-source';
import '@testing-library/jest-dom';
import { act, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi, beforeAll, afterAll } from 'vitest';

const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: toastError } }));

vi.mock('@microsoft/fetch-event-source', () => ({
  fetchEventSource: vi.fn().mockImplementation(() => { throw new Error('SSE Fallback'); })
}));

import OrderManagerView from './OrderManagerView';

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  isClosed = false;
  sentMessages: string[] = [];

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  close() {
    this.isClosed = true;
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  open() {
    this.onopen?.();
  }

  message(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>);
  }
}

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
  beforeAll(() => { vi.spyOn(console, 'warn').mockImplementation(() => {}); vi.spyOn(console, 'error').mockImplementation(() => {}); });
  afterAll(() => { vi.restoreAllMocks(); });

  beforeEach(() => {
    MockWebSocket.instances = [];
    localStorage.setItem('admin_token', 'fake_token');
    vi.stubGlobal('WebSocket', MockWebSocket);

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

  it('connects to the authenticated Order Manager WebSocket', async () => {
    await act(async () => { render(<OrderManagerView />); })

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toEqual(expect.stringContaining('/api/v1/orders/ws?token=fake_token'));

    act(() => MockWebSocket.instances[0].open());
    expect(screen.getAllByText('Conectado (Ao Vivo)')[0]).toBeInTheDocument();
  });

  it('renders new orders and applies updates received from another screen', async () => {
    await act(async () => { render(<OrderManagerView />); })
    const socket = MockWebSocket.instances[0];
    const order = {
      id: 'pedido-123',
      customerName: 'Cliente',
      total: 74.97,
      address: 'Rua A, 10',
      items: [{ name: 'Brownie', quantity: 1 }],
      status: 'accepted',
      createdAt: '2026-08-31T14:48:07.915Z',
    };

    act(() => socket.message({ event: 'new_order', order }));
    expect(screen.getAllByText('Pedido #PEDIDO')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Aceito')[0]).toBeInTheDocument();
    const wazeUrl = new URL(screen.getAllByText('Abrir no Waze')[0].getAttribute('href')!);
    expect(wazeUrl.origin).toBe('https://waze.com');
    expect(wazeUrl.pathname).toBe('/ul');
    expect(wazeUrl.searchParams.get('q')).toBe('Rua A, 10');
    expect(wazeUrl.searchParams.get('navigate')).toBe('yes');
    expect(wazeUrl.searchParams.get('utm_source')).toBe('dominuslabs_order_manager');

    act(() => socket.message({ event: 'order_updated', order: { ...order, status: 'delivered' } }));
    expect(screen.getAllByText('Entregue')[0]).toBeInTheDocument();
  });

  it('closes the socket when the screen is unmounted', async () => {
    let unmount: any; await act(async () => { unmount = render(<OrderManagerView />).unmount; });
    const socket = MockWebSocket.instances[0];

    unmount();

    expect(socket.isClosed).toBe(true);
  });

  it('answers the server heartbeat without treating it as an order event', async () => {
    await act(async () => { render(<OrderManagerView />); })
    const socket = MockWebSocket.instances[0];

    act(() => socket.message({ event: 'ping' }));

    expect(socket.sentMessages).toEqual([JSON.stringify({ event: 'pong' })]);
    expect(screen.getAllByText('Nenhum pedido no momento.')[0]).toBeInTheDocument();
  });

  it('polling brings pending orders even before websocket connects', async () => {
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
    let unmount: any; await act(async () => { unmount = render(<OrderManagerView />).unmount; });

    unmount();

    expect(global.clearInterval).toHaveBeenCalled();
  });
});

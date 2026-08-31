import '@testing-library/jest-dom';
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import OrderManagerView from './OrderManagerView';

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  isClosed = false;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  close() {
    this.isClosed = true;
  }

  open() {
    this.onopen?.();
  }

  message(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>);
  }
}

describe('OrderManagerView', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    localStorage.setItem('admin_token', 'fake_token');
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ orders: [] }),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('connects to the authenticated Order Manager WebSocket', () => {
    render(<OrderManagerView />);

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain('/api/v1/orders/ws?token=fake_token');

    act(() => MockWebSocket.instances[0].open());
    expect(screen.getByText('Conectado (Ao Vivo)')).toBeInTheDocument();
  });

  it('renders new orders and applies updates received from another screen', () => {
    render(<OrderManagerView />);
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
    expect(screen.getByText('Pedido #PEDIDO')).toBeInTheDocument();
    expect(screen.getByText('Aceito')).toBeInTheDocument();
    const wazeUrl = new URL(screen.getByText('Abrir no Waze').getAttribute('href')!);
    expect(wazeUrl.origin).toBe('https://waze.com');
    expect(wazeUrl.pathname).toBe('/ul');
    expect(wazeUrl.searchParams.get('q')).toBe('Rua A, 10');
    expect(wazeUrl.searchParams.get('navigate')).toBe('yes');
    expect(wazeUrl.searchParams.get('utm_source')).toBe('dominuslabs_order_manager');

    act(() => socket.message({ event: 'order_updated', order: { ...order, status: 'delivered' } }));
    expect(screen.getByText('Entregue')).toBeInTheDocument();
  });

  it('closes the socket when the screen is unmounted', () => {
    const { unmount } = render(<OrderManagerView />);
    const socket = MockWebSocket.instances[0];

    unmount();

    expect(socket.isClosed).toBe(true);
  });
});

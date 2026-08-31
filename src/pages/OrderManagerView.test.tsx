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

class MockAudio {
  static instances: MockAudio[] = [];

  src = '';
  currentTime = 0;
  onended: (() => void) | null = null;
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();

  constructor() {
    MockAudio.instances.push(this);
  }
}

class MockURL extends URL {
  static createObjectURL = vi.fn(() => 'blob:order-alarm');
  static revokeObjectURL = vi.fn();
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
  beforeEach(() => {
    MockWebSocket.instances = [];
    MockAudio.instances = [];
    MockURL.createObjectURL.mockClear();
    MockURL.revokeObjectURL.mockClear();
    localStorage.setItem('admin_token', 'fake_token');
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.stubGlobal('Audio', MockAudio);
    vi.stubGlobal('URL', MockURL);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ orders: [] }),
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
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

  it('downloads the TTS once and reuses the loaded audio on every alarm loop', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ orders: [] }) })
      .mockResolvedValueOnce({ ok: true, blob: async () => new Blob(['audio']) });
    vi.stubGlobal('fetch', fetchMock);

    render(<OrderManagerView />);
    const socket = MockWebSocket.instances[0];
    act(() => socket.message({ event: 'new_order', order: pendingOrder }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const audio = MockAudio.instances[0];
    expect(audio.play).toHaveBeenCalledTimes(1);

    act(() => {
      audio.onended?.();
      vi.advanceTimersByTime(10_000);
    });

    expect(audio.play).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('does not start an alarm when a pending TTS request finishes after an order update', async () => {
    let resolveBlob: (blob: Blob) => void = () => undefined;
    const delayedBlob = new Promise<Blob>(resolve => {
      resolveBlob = resolve;
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ orders: [] }) })
      .mockResolvedValueOnce({ ok: true, blob: () => delayedBlob });
    vi.stubGlobal('fetch', fetchMock);

    render(<OrderManagerView />);
    const socket = MockWebSocket.instances[0];
    act(() => socket.message({ event: 'new_order', order: pendingOrder }));
    await act(async () => {
      await Promise.resolve();
    });

    const audio = MockAudio.instances[0];
    act(() => socket.message({ event: 'order_updated', order: { ...pendingOrder, status: 'accepted' } }));
    await act(async () => {
      resolveBlob(new Blob(['audio']));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(audio.play).not.toHaveBeenCalled();
    expect(MockURL.revokeObjectURL).toHaveBeenCalledWith('blob:order-alarm');
  });
});

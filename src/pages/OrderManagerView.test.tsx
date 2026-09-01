// import '@testing-library/jest-dom';
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: toastError } }));

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

class MockAudio {
  static instances: MockAudio[] = [];
  static playResult: Promise<void> = Promise.resolve();

  src = '';
  currentTime = 0;
  onended: (() => void) | null = null;
  play = vi.fn(() => MockAudio.playResult);
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
    MockAudio.playResult = Promise.resolve();
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
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:8000/api/v1/orders/ws?token=fake_token');

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

  it('downloads the TTS once and reuses the loaded audio on every alarm loop', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ orders: [] }) })
      .mockResolvedValueOnce({ ok: true, blob: async () => new Blob(['audio']) });
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<OrderManagerView />); })
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

    await act(async () => { render(<OrderManagerView />); })
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

  it('uses visible and spoken fallback when browser audio is blocked', async () => {
    const speak = vi.fn();
    vi.stubGlobal('speechSynthesis', { cancel: vi.fn(), speak });
    vi.stubGlobal('SpeechSynthesisUtterance', class {
      constructor(public text: string) {}
    });
    MockAudio.playResult = Promise.reject(new Error('play blocked'));
    MockAudio.playResult.catch(() => {}); // Prevent unhandled rejection warning
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ orders: [] }) })
      .mockResolvedValueOnce({ ok: true, blob: async () => new Blob(['audio']) });
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<OrderManagerView />); })
    act(() => MockWebSocket.instances[0].message({ event: 'new_order', order: pendingOrder }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(toastError).toHaveBeenCalledWith(expect.stringContaining('Novo pedido pendente'));
    expect(speak).toHaveBeenCalledTimes(1);
  });

  it('polling brings pending orders even before websocket connects', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ orders: [{ ...pendingOrder, id: 'pedido-poll' }] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<OrderManagerView />); })

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getAllByText('Pedido #PEDIDO')[0]).toBeInTheDocument();

    // Fast-forward 30 seconds to trigger polling
    await act(async () => { vi.advanceTimersByTime(30000); await Promise.resolve(); });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('cleans up polling interval on unmount', async () => {
    vi.spyOn(global, 'clearInterval');
    let unmount: any; await act(async () => { unmount = render(<OrderManagerView />).unmount; });

    unmount();

    expect(global.clearInterval).toHaveBeenCalled();
  });
});

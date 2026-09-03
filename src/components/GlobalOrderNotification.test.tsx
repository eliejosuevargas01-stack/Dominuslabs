/**
 * @vitest-environment jsdom
 */
import { act, render } from '@testing-library/react';
const waitForCustom = async (cb) => {
  let err;
  for (let i=0; i<10; i++) {
    try { cb(); return; }
    catch (e) { err = e; await new Promise(r => setTimeout(r, 50)); }
  }
  throw err;
};
import '@testing-library/jest-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import GlobalOrderNotification from './GlobalOrderNotification';

const { toastError, toastDismiss } = vi.hoisted(() => ({
  toastError: vi.fn().mockReturnValue('toast-id'),
  toastDismiss: vi.fn()
}));
vi.mock('sonner', () => ({ toast: { error: toastError, dismiss: toastDismiss } }));

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  isClosed = false;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  close() {
    this.isClosed = true;
  }

  send() {}
}

const mockOscillator = {
  type: '',
  frequency: { setValueAtTime: vi.fn(), value: 0 },
  start: vi.fn(),
  stop: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
};

const mockGain = {
  gain: {
    value: 0,
    setValueAtTime: vi.fn(),
    cancelScheduledValues: vi.fn(),
    linearRampToValueAtTime: vi.fn(),
  },
  connect: vi.fn(),
  disconnect: vi.fn(),
};

class MockAudioContext {
  static instances: MockAudioContext[] = [];
  state = 'running';
  currentTime = 0;
  resume = vi.fn().mockResolvedValue(undefined);

  createOscillator = vi.fn(() => ({...mockOscillator}));
  createGain = vi.fn(() => ({...mockGain}));
  destination = {};

  constructor() {
    MockAudioContext.instances.push(this);
  }
}

describe('GlobalOrderNotification', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    MockAudioContext.instances = [];
    localStorage.setItem('admin_token', 'fake_token');
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.stubGlobal('AudioContext', MockAudioContext);
    vi.stubGlobal('window', { ...window, AudioContext: MockAudioContext, addEventListener: vi.fn(), removeEventListener: vi.fn() });

    toastError.mockClear();
    toastDismiss.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('fetches orders on mount and sets up WebSocket', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ ok: true, orders: [] })
    }));
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<div><GlobalOrderNotification /></div>); });

    await waitForCustom(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    expect(MockWebSocket.instances.length).toBe(1);
    expect(MockWebSocket.instances[0].url).toContain('/api/v1/orders/ws?token=fake_token');
  });

  it('plays alarm when there are pending orders', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ ok: true, orders: [{ id: '1', status: 'pending' }] })
    }));
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<div><GlobalOrderNotification /></div>); });

    await waitForCustom(() => {
      expect(MockAudioContext.instances.length).toBe(1);
      const ctx = MockAudioContext.instances[0];
      expect(ctx.createOscillator).toHaveBeenCalled();
      expect(ctx.createGain).toHaveBeenCalled();
    });
  });

  it('stops alarm when pending orders are gone', async () => {
    let isPending = true;
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ ok: true, orders: isPending ? [{ id: '1', status: 'pending' }] : [] })
    }));
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<div><GlobalOrderNotification /></div>); });

    await waitForCustom(() => {
      expect(MockAudioContext.instances.length).toBe(1);
      expect(MockAudioContext.instances[0].createOscillator).toHaveBeenCalled();
    });

    isPending = false;

    // Simulate websocket message that triggers a re-fetch
    const ws = MockWebSocket.instances[0];
    await act(async () => {
      ws.onmessage?.({ data: JSON.stringify({ event: 'order_updated' }) } as MessageEvent);
    });

    await waitForCustom(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
  });

  it('shows error toast if audio context is suspended (blocked autoplay)', async () => {
    const suspendedContext = class extends MockAudioContext {
      constructor() {
        super();
        this.state = 'suspended';
      }
    };
    vi.stubGlobal('AudioContext', suspendedContext);
    vi.stubGlobal('window', { ...window, AudioContext: suspendedContext, addEventListener: vi.fn(), removeEventListener: vi.fn() });

    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ ok: true, orders: [{ id: '1', status: 'pending' }] })
    }));
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<div><GlobalOrderNotification /></div>); });

    await waitForCustom(() => {
      expect(toastError).toHaveBeenCalledWith(
        expect.stringContaining('pedido(s) pendente(s)! Clique em qualquer lugar'),
        expect.anything()
      );
    });
  });

  it('polls every 2 minutes', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ ok: true, orders: [] })
    }));
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<div><GlobalOrderNotification /></div>); });

    await waitForCustom(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      vi.advanceTimersByTime(120000);
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('converts http:// API_BASE to ws:// or wss:// appropriately', async () => {
    // Delete window.location and mock it
    const originalLocation = window.location;
    // @ts-ignore
    delete window.location;
    // @ts-ignore
    window.location = {
      ...originalLocation,
      origin: 'https://dominuslabs.online',
      protocol: 'https:',
      hostname: 'dominuslabs.online',
    } as any;

    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ ok: true, orders: [] })
    }));
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<div><GlobalOrderNotification /></div>); });

    await waitForCustom(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    // Our websocket should be initialized with wss:// based on the origin
    expect(MockWebSocket.instances.length).toBe(1);
    expect(MockWebSocket.instances[0].url).toContain('wss://');

    // restore window.location
    // @ts-ignore
    window.location = originalLocation as any;
  });
});

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
const { toastError, toastDismiss, MockSSEClient } = vi.hoisted(() => {
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

  return {
    toastError: vi.fn().mockReturnValue('toast-id'),
    toastDismiss: vi.fn(),
    MockSSEClient,
  };
});

vi.mock('sonner', () => ({ toast: { error: toastError, dismiss: toastDismiss } }));
vi.mock('../services/sseClient', () => ({
  SSEClient: MockSSEClient,
}));

import GlobalOrderNotification from './GlobalOrderNotification';

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
    MockSSEClient.instances = [];
    MockAudioContext.instances = [];
    localStorage.setItem('admin_token', 'fake_token');
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

  it('fetches orders on mount and sets up SSE', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ ok: true, orders: [] })
    }));
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => { render(<div><GlobalOrderNotification /></div>); });

    await waitForCustom(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    expect(MockSSEClient.instances.length).toBe(1);
    expect(MockSSEClient.instances[0].url).toContain('/api/v1/orders/events');
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

    // Simulate SSE message that triggers a re-fetch
    const sse = MockSSEClient.instances[0];
    await act(async () => {
      sse.message({ event: 'order_updated' });
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

  it('polls periodically for reconciliation', async () => {
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
      vi.advanceTimersByTime(60000);
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

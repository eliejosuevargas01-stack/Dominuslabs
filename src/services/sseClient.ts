import { fetchEventSource, type EventSourceMessage } from '@microsoft/fetch-event-source';
import { getValidAccessToken, refreshAuthTokenSilently } from './api';

export class SSEAuthError extends Error {
  constructor(message = 'SSE authentication failed and refresh token is unavailable') {
    super(message);
    this.name = 'SSEAuthError';
  }
}

export interface SSEClientOptions {
  url: string;
  onMessage: (data: any, event?: string) => void;
  onOpen?: () => void;
  onError?: (error: any) => void;
  onClose?: () => void;
}

export class SSEClient {
  private controller: AbortController | null = null;
  private url: string;
  private onMessage: (data: any, event?: string) => void;
  private onOpen?: () => void;
  private onError?: (error: any) => void;
  private onClose?: () => void;
  private isClosedManually = false;
  private retryCount = 0;
  private retryTimeout: any = null;

  constructor(options: SSEClientOptions) {
    this.url = options.url;
    this.onMessage = options.onMessage;
    this.onOpen = options.onOpen;
    this.onError = options.onError;
    this.onClose = options.onClose;
  }

  public async connect(): Promise<void> {
    this.isClosedManually = false;
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }
    if (this.controller) {
      this.controller.abort();
      this.controller = null;
    }

    const token = await getValidAccessToken();
    if (!token) {
      const authErr = new SSEAuthError('No valid token available');
      if (this.onError) this.onError(authErr);
      this.disconnect();
      return;
    }

    this.controller = new AbortController();

    try {
      await fetchEventSource(this.url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        signal: this.controller.signal,
        onopen: async (response) => {
          if (response.ok) {
            this.retryCount = 0;
            if (this.onOpen) this.onOpen();
            return;
          }
          if (response.status === 401) {
            const newToken = await refreshAuthTokenSilently();
            if (newToken) {
              throw new Error('Token refreshed, reconnecting');
            }
            throw new SSEAuthError('SSE authentication failed: session expired or token refresh failed');
          }
          throw new Error(`SSE open failed with status ${response.status}`);
        },
        onmessage: (msg: EventSourceMessage) => {
          if (!msg.data || msg.data.trim() === 'ping' || msg.data.trim() === 'connected') {
            return;
          }
          try {
            const parsed = JSON.parse(msg.data);
            this.onMessage(parsed, msg.event);
          } catch {
            this.onMessage(msg.data, msg.event);
          }
        },
        onclose: () => {
          if (!this.isClosedManually) {
            if (this.onClose) this.onClose();
            this.scheduleReconnect();
          }
        },
        onerror: (err) => {
          if (this.isClosedManually) return;
          if (err instanceof SSEAuthError || (err as any)?.name === 'SSEAuthError') {
            if (this.onError) this.onError(err);
            this.disconnect();
            throw err;
          }
          if (this.onError) this.onError(err);
          throw err;
        }
      });
    } catch (e: any) {
      if (!this.isClosedManually) {
        if (e instanceof SSEAuthError || e?.name === 'SSEAuthError') {
          this.disconnect();
        } else {
          this.scheduleReconnect();
        }
      }
    }
  }

  private scheduleReconnect() {
    if (this.isClosedManually) return;
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }

    const backoff = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
    this.retryCount++;
    this.retryTimeout = setTimeout(() => {
      this.connect();
    }, backoff);
  }

  public disconnect(): void {
    this.isClosedManually = true;
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }
    if (this.controller) {
      this.controller.abort();
      this.controller = null;
    }
    if (this.onClose) {
      this.onClose();
    }
  }
}

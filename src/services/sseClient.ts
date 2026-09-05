import { fetchEventSource, type EventSourceMessage } from '@microsoft/fetch-event-source';
import { getValidAccessToken, refreshAuthTokenSilently } from './api';

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
    }
    this.controller = new AbortController();

    const token = await getValidAccessToken();
    if (!token) {
      if (this.onError) this.onError(new Error('No valid token available'));
      return;
    }

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
          if (this.onError) this.onError(err);
          this.scheduleReconnect();
          throw err;
        }
      });
    } catch (e) {
      if (!this.isClosedManually) {
        this.scheduleReconnect();
      }
    }
  }

  private scheduleReconnect() {
    if (this.isClosedManually) return;
    if (this.retryTimeout) clearTimeout(this.retryTimeout);

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

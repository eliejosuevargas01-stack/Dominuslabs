import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { API_BASE, handleExpiredSessionRedirect, decodeJwtExp } from '../services/api';

// Type from the backend order schema
interface Order {
  id: string;
  status: string;
}

const getWebSocketUrl = () => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  const origin = typeof window !== 'undefined' && window.location ? (window.location.origin || 'http://localhost:8000') : 'http://localhost:8000';
  const resolvedUrl = new URL(API_BASE, origin);
  const wsProto = resolvedUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  const pathname = resolvedUrl.pathname.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
  return `${wsProto}//${resolvedUrl.host}${pathname}`;
};

export default function GlobalOrderNotification() {
  const [pendingCount, setPendingCount] = useState(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const oscillatorRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const isPlayingRef = useRef(false);
  const audioBlockedToastIdRef = useRef<string | number | null>(null);
  const unlockAudioListenerRef = useRef<(() => void) | null>(null);

  const removeUnlockListeners = () => {
    if (unlockAudioListenerRef.current) {
      window.removeEventListener('click', unlockAudioListenerRef.current);
      window.removeEventListener('keydown', unlockAudioListenerRef.current);
      window.removeEventListener('touchstart', unlockAudioListenerRef.current);
      unlockAudioListenerRef.current = null;
    }
  };

  // Ref for polling interval to prevent stale closure
  const fetchOrders = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      if (!token) return;

      const response = await fetch(`${API_BASE}/orders`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        if (response.status === 401) {
          handleExpiredSessionRedirect();
        }
        return;
      }

      const data = await response.json();
      if (data.ok && Array.isArray(data.orders)) {
        const pCount = data.orders.filter((o: Order) => o.status === 'pending').length;
        setPendingCount(pCount);
      }
    } catch (e) {
      console.error('Erro ao buscar pedidos no alarme global', e);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) return;

    const exp = decodeJwtExp(token);
    if (exp && Date.now() >= exp * 1000) {
      handleExpiredSessionRedirect();
      return;
    }

    let socket: WebSocket | null = null;
    let eventSource: EventSource | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let disposed = false;

    const connectRealtime = () => {
      if (disposed) return;

      // Primary: EventSource (SSE) - 100% compatible with reverse proxies, Caddy, Cloudflare, etc.
      if (typeof window !== 'undefined' && typeof window.EventSource !== 'undefined') {
        try {
          const sseUrl = `${API_BASE}/orders/events?token=${encodeURIComponent(token)}`;
          eventSource = new EventSource(sseUrl);

          eventSource.onopen = () => {
            if (disposed) { eventSource?.close(); return; }
            console.log('[GlobalOrderNotification] SSE conectado');
          };

          eventSource.onmessage = (event) => {
            if (!event.data || event.data.startsWith(':')) return;
            try {
              const data = JSON.parse(event.data);
              if (data.event === 'new_order' || data.event === 'order_updated') {
                fetchOrders();
              }
            } catch (e) {
              console.error('[GlobalOrderNotification] Erro ao processar mensagem SSE', e);
            }
          };

          eventSource.onerror = () => {
            try { eventSource?.close(); } catch (_) {}
            if (disposed) return;
            console.log('[GlobalOrderNotification] SSE desconectado. Tentando reconectar em 15s...');
            reconnectTimeout = setTimeout(connectRealtime, 15000);
          };
          return;
        } catch (e) {
          console.warn('[GlobalOrderNotification] Falha ao iniciar SSE, tentando fallback WebSocket...', e);
        }
      }

      // Fallback: WebSocket
      const wsBase = getWebSocketUrl();
      socket = new WebSocket(`${wsBase}/api/v1/orders/ws?token=${encodeURIComponent(token)}`);

      socket.onopen = () => {
        if (disposed) {
          try { socket?.close(1000, 'Unmounted'); } catch (_) {}
          return;
        }
        console.log('[GlobalOrderNotification] WebSocket conectado');
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'ping') {
            socket?.send(JSON.stringify({ event: 'pong' }));
            return;
          }
          if (data.event === 'new_order' || data.event === 'order_updated') {
            // Reconciliate the pending count
            fetchOrders();
          }
        } catch (e) {
          console.error('[GlobalOrderNotification] Erro ao processar mensagem WS', e);
        }
      };

      socket.onclose = () => {
        if (disposed) return;
        console.log('[GlobalOrderNotification] WebSocket desconectado. Tentando reconectar...');
        reconnectTimeout = setTimeout(connectRealtime, 5000);
      };

      socket.onerror = () => {
        if (disposed) return;
        console.warn('[GlobalOrderNotification] WebSocket aviso/desconexão', {
          url: socket?.url,
          readyState: socket?.readyState,
        });
      };
    };

    connectRealtime();
    fetchOrders(); // Initial fetch

    // Polling every 2 minutes as fallback
    const intervalId = setInterval(fetchOrders, 2 * 60 * 1000);

    return () => {
      disposed = true;
      clearTimeout(reconnectTimeout);
      clearInterval(intervalId);
      if (eventSource) {
        eventSource.onopen = null;
        eventSource.onmessage = null;
        eventSource.onerror = null;
        eventSource.close();
      }
      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        if (socket.readyState === WebSocket.OPEN) {
          socket.close(1000, 'Unmounted');
        } else {
          // If still connecting, wait for open before closing to avoid "closed before established" warning
          socket.onopen = () => {
            try { socket?.close(1000, 'Unmounted'); } catch (_) {}
          };
        }
      }
    };
  }, []);

  // Manage Web Audio API sound based on pendingCount
  useEffect(() => {
    if (pendingCount > 0) {
      startAlarm();
    } else {
      stopAlarm();
    }

    // Cleanup on unmount or pendingCount change
    return () => stopAlarm();
  }, [pendingCount]);

  const startAlarm = async () => {
    if (isPlayingRef.current) return;

    try {
      if (!audioContextRef.current) {
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        if (!AudioContext) {
            console.warn('Web Audio API não suportada neste navegador.');
            return;
        }
        audioContextRef.current = new AudioContext();
      }

      // Resume context if suspended (browser autoplay policy)
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }

      // If still suspended after resume attempt, autoplay is hard-blocked
      if (audioContextRef.current.state === 'suspended') {
        if (!audioBlockedToastIdRef.current) {
            audioBlockedToastIdRef.current = toast.error(
                `Há ${pendingCount} pedido(s) pendente(s)! Clique em qualquer lugar ou interaja com a página para ativar o alarme sonoro.`,
                { duration: Infinity }
            );
        }

        // Clean up any stale listeners first
        removeUnlockListeners();

        // Setup a one-time interaction listener to unlock audio
        const unlockAudio = async () => {
            if (audioContextRef.current?.state === 'suspended') {
                await audioContextRef.current.resume();
                if ((audioContextRef.current.state as string) === 'running') {
                    if (audioBlockedToastIdRef.current) {
                        toast.dismiss(audioBlockedToastIdRef.current);
                        audioBlockedToastIdRef.current = null;
                    }
                    if (pendingCount > 0 && !isPlayingRef.current) {
                        playOscillator();
                    }
                }
            }
            removeUnlockListeners();
        };

        unlockAudioListenerRef.current = unlockAudio;
        window.addEventListener('click', unlockAudio);
        window.addEventListener('keydown', unlockAudio);
        window.addEventListener('touchstart', unlockAudio);

        return; // Wait for user interaction
      }

      playOscillator();

    } catch (e) {
      console.error('[GlobalOrderNotification] Falha ao iniciar alarme:', e);
      if (!audioBlockedToastIdRef.current) {
          audioBlockedToastIdRef.current = toast.error(`Novo(s) pedido(s) pendente(s)! Verifique o Order Manager.`, { duration: 10000 });
      }
    }
  };

  const playOscillator = () => {
    if (!audioContextRef.current || isPlayingRef.current) return;

    // Very noticeable, annoying sound pattern in a loop
    const ctx = audioContextRef.current;

    const osc = ctx.createOscillator();
    const gainNode = ctx.createGain();

    osc.type = 'square'; // Harsh sound
    osc.frequency.setValueAtTime(800, ctx.currentTime);

    // Create an LFO to modulate the frequency for an alarm effect (siren-like)
    const lfo = ctx.createOscillator();
    lfo.type = 'sine';
    lfo.frequency.value = 5; // 5 times a second
    const lfoGain = ctx.createGain();
    lfoGain.gain.value = 100;

    lfo.connect(lfoGain);
    lfoGain.connect(osc.frequency);

    // Pulse the volume
    gainNode.gain.setValueAtTime(0, ctx.currentTime);

    // Create a loop with setInterval to re-trigger the pulse envelope
    const interval = setInterval(() => {
        if (!gainNodeRef.current) return;
        const now = ctx.currentTime;
        gainNode.gain.cancelScheduledValues(now);
        gainNode.gain.setValueAtTime(0, now);
        gainNode.gain.linearRampToValueAtTime(0.5, now + 0.1);
        gainNode.gain.setValueAtTime(0.5, now + 0.3);
        gainNode.gain.linearRampToValueAtTime(0, now + 0.4);
    }, 1000);

    osc.connect(gainNode);
    gainNode.connect(ctx.destination);

    lfo.start();
    osc.start();

    oscillatorRef.current = osc;
    gainNodeRef.current = gainNode;
    isPlayingRef.current = true;

    // Store interval to clear it on stop
    (oscillatorRef.current as any)._pulseInterval = interval;
    (oscillatorRef.current as any)._lfo = lfo;
  };

  const stopAlarm = () => {
    removeUnlockListeners();

    if (audioBlockedToastIdRef.current) {
        toast.dismiss(audioBlockedToastIdRef.current);
        audioBlockedToastIdRef.current = null;
    }

    if (oscillatorRef.current) {
      try {
        const interval = (oscillatorRef.current as any)._pulseInterval;
        if (interval) clearInterval(interval);

        const lfo = (oscillatorRef.current as any)._lfo;
        if (lfo) lfo.stop();

        oscillatorRef.current.stop();
        oscillatorRef.current.disconnect();
      } catch (e) {
        // ignore if already stopped
      }
      oscillatorRef.current = null;
    }

    if (gainNodeRef.current) {
      gainNodeRef.current.disconnect();
      gainNodeRef.current = null;
    }

    isPlayingRef.current = false;
  };

  // Render nothing, it's a headless notification component
  return null;
}

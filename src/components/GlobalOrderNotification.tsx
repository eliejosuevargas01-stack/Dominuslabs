import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { 
  API_BASE, 
  fetchWithAuth 
} from '../services/api';
import { SSEClient } from '../services/sseClient';

// Type from the backend order schema
interface Order {
  id: string;
  status: string;
}

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
      const response = await fetchWithAuth(`${API_BASE}/orders`);
      if (!response.ok) return;

      const data = await response.json();
      if (data.ok && Array.isArray(data.orders)) {
        const pCount = data.orders.filter((o: Order) => o.status === 'pending').length;
        setPendingCount(pCount);
      }
    } catch (e) {
      console.warn('[GlobalOrderNotification] Aviso ao sincronizar pedidos:', e);
    }
  };

  useEffect(() => {
    let sseClient: SSEClient | null = null;
    let disposed = false;

    const connectRealtime = () => {
      if (disposed) return;
      sseClient = new SSEClient({
        url: `${API_BASE}/orders/events`,
        onMessage: (data) => {
          if (!data) return;
          if (data.event === 'new_order') {
            fetchOrders();
          } else if (data.event === 'order_updated') {
            if (data.order && data.order.status !== 'pending') {
              stopAlarm();
              setPendingCount(prev => Math.max(0, prev - 1));
            }
            fetchOrders();
          }
        },
        onOpen: () => {
          console.log('[GlobalOrderNotification] SSE conectado via Authorization: Bearer');
        },
        onError: (e) => {
          console.warn('[GlobalOrderNotification] Aviso/reconectando SSE:', e);
        }
      });
      sseClient.connect();
    };

    const handleTokenRefreshed = () => {
      if (disposed) return;
      console.log('[GlobalOrderNotification] Token renovado detectado por evento. Reconectando...');
      sseClient?.disconnect();
      connectRealtime();
    };

    const handleOrderActionTaken = () => {
      console.log('[GlobalOrderNotification] Pedido aceito ou rejeitado. Silenciando alarme imediatamente...');
      stopAlarm();
      setPendingCount(0);
      setTimeout(fetchOrders, 1000);
    };

    window.addEventListener('token_refreshed', handleTokenRefreshed);
    window.addEventListener('order_action_taken', handleOrderActionTaken);

    connectRealtime();
    fetchOrders(); // Initial fetch

    // Reconciliação eventual periódica a cada 60s
    const intervalId = setInterval(fetchOrders, 60 * 1000);

    return () => {
      disposed = true;
      window.removeEventListener('token_refreshed', handleTokenRefreshed);
      window.removeEventListener('order_action_taken', handleOrderActionTaken);
      clearInterval(intervalId);
      sseClient?.disconnect();
      stopAlarm();
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

import { useState, useEffect, useRef } from 'react';
import { ShoppingBag, Check, MapPin, DollarSign, Clock } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Documentation-Driven Testing:
 * O comportamento esperado para OrderManagerView.tsx:
 * - `useOrdersWebSocket`: Conecta via WebSocket à `/api/v1/orders/ws`. Recebe eventos `new_order` e `order_updated`.
 * - `Card de Pedido`: Exibe detalhes do pedido (nome, valor, endereço, itens).
 * - `Botão Aceitar`: Para o loop de áudio e atualiza o status do pedido localmente ou via API.
 * - `Link Waze`: Abre uma rota de navegação HTTPS com endereço codificado.
 * - `Áudio TTS`: Toca em loop "Olá..." a cada 15s até aceitar o pedido.
 */

// API Base URL (adjust for testing/prod)
import { 
  API_BASE, 
  fetchWithAuth, 
  getStoredAccessToken, 
  isTokenExpired, 
  refreshAuthTokenSilently 
} from "../services/api";

interface OrderItem {
  name: string;
  quantity: number;
}

interface Order {
  id: string;
  customerName: string;
  total: number;
  address: string;
  items: OrderItem[];
  status: 'pending' | 'accepted' | 'ready_for_delivery' | 'out_for_delivery' | 'delivered' | 'completed' | 'cancelled';
  createdAt: string;
}

type OperationalStatus = 'ready_for_delivery' | 'out_for_delivery' | 'delivered';

type ActiveAlarm = {
  audio: HTMLAudioElement;
  abortController: AbortController;
  interval?: ReturnType<typeof setTimeout>;
  blobUrl?: string;
};

function buildWazeNavigationUrl(address: string): string | null {
  const normalizedAddress = address.trim().replace(/\s+/g, ' ');
  if (!normalizedAddress) return null;

  const url = new URL('https://waze.com/ul');
  url.searchParams.set('q', normalizedAddress);
  url.searchParams.set('navigate', 'yes');
  url.searchParams.set('utm_source', 'dominuslabs_order_manager');
  return url.toString();
}

const statusLabels: Record<string, string> = {
  pending: 'Pendente',
  accepted: 'Aceito',
  ready_for_delivery: 'Pronto para entrega',
  out_for_delivery: 'Saiu para entrega',
  delivered: 'Entregue',
  completed: 'Concluído',
  rejected: 'Recusado',
  cancelled: 'Cancelado',
};

// Custom Hook for real-time Orders
function useOrdersWebSocket() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [announcedOrderIds, setAnnouncedOrderIds] = useState<Set<string>>(new Set());
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    let websocket: WebSocket | null = null;
    let eventSource: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let pollingTimer: ReturnType<typeof setInterval> | null = null;
    let disposed = false;

    const fetchOrders = () => {
        fetchWithAuth(`${API_BASE}/orders`)
          .then(response => {
            if (!response || !response.ok) {
              throw new Error('Falha ao carregar pedidos persistidos');
            }
            return response.json();
          })
          .then(data => {
            if (Array.isArray(data?.orders)) {
              let newIds: string[] = [];
              setOrders(prev => {
                const byId = new Map<string, Order>(prev.map(order => [order.id, order] as [string, Order]));
                data.orders.forEach((incoming: Order) => {
                  if (!byId.has(incoming.id) && incoming.status === 'pending') {
                    newIds.push(incoming.id);
                  }
                  byId.set(incoming.id, incoming);
                });
                return Array.from(byId.values());
              });
              if (newIds.length > 0) {
                setAnnouncedOrderIds(prev => {
                  const newSet = new Set(prev);
                  newIds.forEach(id => newSet.add(id));
                  return newSet;
                });
              }
            }
          })
          .catch(error => console.warn('[OrderManager] Aviso ao carregar pedidos:', error));
    };

    const connect = () => {
      if (disposed) return;

      const token = getStoredAccessToken();
      if (!token) {
        setConnectionStatus('disconnected');
        return;
      }

      if (isTokenExpired(token)) {
        refreshAuthTokenSilently().then(newToken => {
          if (disposed) return;
          if (newToken) connect();
        });
        return;
      }

      setConnectionStatus('connecting');

      // Primary: EventSource (SSE) - 100% compatible with reverse proxies, Caddy, Cloudflare, etc.
      if (typeof window !== 'undefined' && typeof window.EventSource !== 'undefined') {
        try {
          const sseUrl = `${API_BASE}/orders/events?token=${encodeURIComponent(token)}`;
          const es = new EventSource(sseUrl);
          eventSource = es;

          es.onopen = () => {
            if (disposed) {
              es.close();
              return;
            }
            setConnectionStatus('connected');
          };

          es.onmessage = (event) => {
            if (!event.data || event.data.startsWith(':')) return;
            try {
              const data = JSON.parse(event.data);
              if (data.event === 'new_order' && data.order) {
                setAnnouncedOrderIds(prev => new Set(prev).add(data.order.id));
                setOrders(prev => prev.some(order => order.id === data.order.id) ? prev : [data.order, ...prev]);
              } else if (data.event === 'order_updated' && data.order) {
                if (data.order.status !== 'pending') {
                  setAnnouncedOrderIds(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(data.order.id);
                    return newSet;
                  });
                  window.dispatchEvent(new CustomEvent('order_action_taken', { detail: { orderId: data.order.id, status: data.order.status } }));
                }
                setOrders(prev => prev.map(order => order.id === data.order.id ? data.order : order));
              }
            } catch (error) {
              console.error('Erro ao processar evento SSE de pedidos:', error);
            }
          };

          es.onerror = async () => {
            try { es.close(); } catch (_) {}
            if (disposed) return;
            setConnectionStatus('disconnected');
            // Tenta renovar silenciosamente por baixo dos panos antes da próxima tentativa
            await refreshAuthTokenSilently();
            reconnectTimer = setTimeout(connect, 5000);
          };
          return;
        } catch (error) {
          console.warn('[OrderManager] Falha ao iniciar SSE, tentando WebSocket fallback...', error);
        }
      }

      // Fallback: WebSocket
      try {
        const websocketBase = API_BASE.replace(/^http/, 'ws');
        websocket = new WebSocket(`${websocketBase}/orders/ws?token=${encodeURIComponent(token || '')}`);
        websocket.onopen = () => {
          if (disposed) {
            try { websocket?.close(1000, 'Unmounted'); } catch (_) {}
            return;
          }
          setConnectionStatus('connected');
        };
        websocket.onmessage = event => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'ping') {
              websocket?.send(JSON.stringify({ event: 'pong' }));
            } else if (data.event === 'new_order' && data.order) {
              setAnnouncedOrderIds(prev => new Set(prev).add(data.order.id));
              setOrders(prev => prev.some(order => order.id === data.order.id) ? prev : [data.order, ...prev]);
            } else if (data.event === 'order_updated' && data.order) {
              if (data.order.status !== 'pending') {
                setAnnouncedOrderIds(prev => {
                  const newSet = new Set(prev);
                  newSet.delete(data.order.id);
                  return newSet;
                });
                window.dispatchEvent(new CustomEvent('order_action_taken', { detail: { orderId: data.order.id, status: data.order.status } }));
              }
              setOrders(prev => prev.map(order => order.id === data.order.id ? data.order : order));
            }
          } catch (error) {
            console.error('Erro ao processar mensagem do WebSocket:', error);
          }
        };
        websocket.onerror = () => {
          if (disposed) return;
          console.warn('[OrderManager] WebSocket aviso/desconexão', {
            url: websocket?.url,
            readyState: websocket?.readyState,
          });
          websocket?.close();
        };
        websocket.onclose = async () => {
          if (disposed) return;
          setConnectionStatus('disconnected');
          await refreshAuthTokenSilently();
          reconnectTimer = setTimeout(connect, 5000);
        };
      } catch (error) {
        console.error('Falha ao iniciar WebSocket:', error);
        setConnectionStatus('disconnected');
      }
    };

    const handleTokenRefreshed = () => {
      if (disposed) return;
      console.log('[OrderManager] Token renovado detectado por evento global. Reconectando...');
      if (eventSource) {
        try { eventSource.close(); } catch (_) {}
        eventSource = null;
      }
      if (websocket) {
        try { websocket.close(); } catch (_) {}
        websocket = null;
      }
      connect();
    };

    window.addEventListener('token_refreshed', handleTokenRefreshed);

    // The database is the durable source of truth. This reconciliation keeps
    // the screen current even when a WebSocket is connected to another app
    // worker than the one which received the n8n webhook.
    fetchOrders();
    pollingTimer = setInterval(fetchOrders, 120000);
    connect();

    return () => {
      disposed = true;
      window.removeEventListener('token_refreshed', handleTokenRefreshed);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pollingTimer) clearInterval(pollingTimer);
      if (eventSource) {
        eventSource.onopen = null;
        eventSource.onmessage = null;
        eventSource.onerror = null;
        eventSource.close();
      }
      if (websocket) {
        websocket.onopen = null;
        websocket.onmessage = null;
        websocket.onerror = null;
        websocket.onclose = null;
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.close(1000, 'Unmounted');
        } else {
          websocket.onopen = () => {
            try { websocket?.close(1000, 'Unmounted'); } catch (_) {}
          };
        }
      }
    };
  }, []);

  return { orders, setOrders, announcedOrderIds, connectionStatus };
}

export default function OrderManagerView() {
  const { orders, setOrders, announcedOrderIds, connectionStatus } = useOrdersWebSocket();
  const activeAlarms = useRef<Record<string, ActiveAlarm>>({});

  const announceAudioFallback = (order: Order) => {
    const message = `Novo pedido pendente ${order.id}. Ative o som desta tela.`;
    toast.error(message);
    if ('speechSynthesis' in window && 'SpeechSynthesisUtterance' in window) {
      // window.speechSynthesis.cancel(); // Removed to prevent silencing other pending orders
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(message));
    }
  };

  useEffect(() => {
    // Check for new pending orders and start alarm
    orders.forEach(order => {
      if (order.status === 'pending' && announcedOrderIds.has(order.id) && !activeAlarms.current[order.id]) {
        playAlarm(order);
      }
    });

    // Cleanup alarms for non-pending orders (just in case)
    Object.keys(activeAlarms.current).forEach(orderId => {
      const order = orders.find(o => o.id === orderId);
      if (!order || order.status !== 'pending') {
        stopAlarm(orderId);
      }
    });

  }, [orders, announcedOrderIds]);

  const playAlarm = (order: Order) => {
    const audio = new Audio();
    const abortController = new AbortController();
    activeAlarms.current[order.id] = { audio, abortController };

    const replay = () => {
      const alarm = activeAlarms.current[order.id];
      if (!alarm || alarm.audio !== audio) return;

      audio.currentTime = 0;
      void audio.play().catch(() => announceAudioFallback(order));
    };

    audio.onended = () => {
      // Repete o alarme após 10 segundos de silêncio
      const alarm = activeAlarms.current[order.id];
      if (!alarm || alarm.audio !== audio) return;
      alarm.interval = setTimeout(replay, 10000);
    };

    void (async () => {
      try {
        const response = await fetchWithAuth(`${API_BASE}/orders/${encodeURIComponent(order.id)}/tts-alarm`, {
          signal: abortController.signal,
        });
        if (!response.ok) throw new Error('Falha ao carregar TTS');

        const blobUrl = URL.createObjectURL(await response.blob());
        const alarm = activeAlarms.current[order.id];
        if (abortController.signal.aborted || !alarm || alarm.audio !== audio) {
          URL.revokeObjectURL(blobUrl);
          return;
        }

        alarm.blobUrl = blobUrl;
        audio.src = blobUrl;
        try {
          await audio.play();
        } catch (error) {
          const errorName = typeof error === 'object' && error !== null && 'name' in error
            ? String(error.name)
            : '';
          if (!abortController.signal.aborted && errorName !== 'AbortError') {
            console.error('Erro ao iniciar alarme neural:', error);
            announceAudioFallback(order);
          }
        }
      } catch (error) {
        if (!abortController.signal.aborted) {
          console.error('Erro ao tocar alarme neural:', error);
          announceAudioFallback(order);
        }
      }
    })();
  };

  const stopAlarm = (orderId: string) => {
    const alarm = activeAlarms.current[orderId];
    if (!alarm) return;

    // Remove primeiro para que uma requisição TTS que termine em paralelo não
    // consiga iniciar um alarme depois de o pedido já ter sido aceito.
    delete activeAlarms.current[orderId];
    alarm.abortController.abort();
    if (alarm.interval) clearTimeout(alarm.interval);
    alarm.audio.onended = null;
    alarm.audio.pause();
    alarm.audio.currentTime = 0;
    if (alarm.blobUrl) URL.revokeObjectURL(alarm.blobUrl);
  };

  // Cleanup all on unmount
  useEffect(() => {
    return () => {
      Object.keys(activeAlarms.current).forEach(stopAlarm);
    };
  }, []);

  const handleAccept = async (orderId: string) => {
    stopAlarm(orderId);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      // window.speechSynthesis.cancel(); // Removed to prevent silencing other pending orders
    }
    window.dispatchEvent(new CustomEvent('order_action_taken', { detail: { orderId, status: 'accepted' } }));
    try {
      const response = await fetchWithAuth(`${API_BASE}/orders/${encodeURIComponent(orderId)}/accept`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Falha ao confirmar pedido');
      const data = await response.json();
      setOrders(prev => prev.map(o => o.id === orderId ? data.order : o));
      toast.success('Pedido aceito com sucesso!');
    } catch {
      toast.error('Não foi possível confirmar o pedido.');
    }
  };

  const handleReject = async (orderId: string) => {
    stopAlarm(orderId);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      // window.speechSynthesis.cancel(); // Removed to prevent silencing other pending orders
    }
    window.dispatchEvent(new CustomEvent('order_action_taken', { detail: { orderId, status: 'rejected' } }));
    try {
      const response = await fetchWithAuth(`${API_BASE}/orders/${encodeURIComponent(orderId)}/reject`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Falha ao recusar pedido');
      const data = await response.json();
      setOrders(prev => prev.map(o => o.id === orderId ? data.order : o));
      toast.success('Pedido recusado com sucesso!');
    } catch {
      toast.error('Não foi possível recusar o pedido.');
    }
  };

  const handleStatusChange = async (orderId: string, nextStatus: OperationalStatus) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/orders/${encodeURIComponent(orderId)}/status?status=${nextStatus}`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Falha ao atualizar status');
      const data = await response.json();
      setOrders(prev => prev.map(o => o.id === orderId ? data.order : o));
      toast.success(`Pedido marcado como ${statusLabels[nextStatus].toLowerCase()}.`);
    } catch {
      toast.error('Não foi possível atualizar o status do pedido.');
    }
  };

  return (
    <div className="p-6 h-full flex flex-col bg-zinc-50">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <ShoppingBag className="w-7 h-7 text-purple-600" />
            Order Manager (PDV)
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Gerencie os pedidos em tempo real.</p>
        </div>
        <div className="flex items-center gap-2 text-sm bg-white border border-zinc-200 px-3 py-1.5 rounded-full shadow-sm">
           <span className={`w-2 h-2 rounded-full ${connectionStatus === 'connected' ? 'bg-emerald-500 animate-pulse' : connectionStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'}`}></span>
           <span className="text-zinc-600 font-medium">
             {connectionStatus === 'connected' ? 'Conectado (Ao Vivo)' : connectionStatus === 'connecting' ? 'Conectando...' : 'Desconectado'}
           </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-max flex-1 overflow-y-auto pb-20">
        {orders.length === 0 ? (
          <div className="col-span-full flex flex-col items-center justify-center p-12 text-zinc-400 bg-white border border-dashed border-zinc-200 rounded-xl">
             <ShoppingBag className="w-12 h-12 mb-4 opacity-50" />
             <p className="text-lg font-medium text-zinc-600">Nenhum pedido no momento.</p>
             <p className="text-sm">Aguardando novos pedidos...</p>
          </div>
        ) : (
          orders.map((order) => (
            <div
              key={order.id}
              className={`bg-white rounded-xl border ${order.status === 'pending' ? 'border-purple-300 shadow-md ring-1 ring-purple-100' : 'border-zinc-200 shadow-sm'} overflow-hidden transition-all`}
            >
              <div className={`p-4 border-b ${order.status === 'pending' ? 'bg-purple-50/50' : 'bg-zinc-50/50'} flex justify-between items-start`}>
                 <div>
                   <h3 className="font-semibold text-lg text-zinc-900">Pedido #{order.id.slice(0,6).toUpperCase()}</h3>
                   <div className="flex items-center gap-1.5 text-zinc-500 text-sm mt-1">
                     <Clock className="w-3.5 h-3.5" />
                     {new Date(order.createdAt).toLocaleTimeString()}
                   </div>
                 </div>
                 <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${
                    order.status === 'pending' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                    order.status === 'accepted' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    'bg-zinc-100 text-zinc-600 border-zinc-200'
                 }`}>
                   {statusLabels[order.status] || order.status}
                 </span>
              </div>

              <div className="p-4 space-y-4">
                <div>
                   <p className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-1">Cliente</p>
                   <p className="font-medium text-zinc-900">{order.customerName}</p>
                </div>

                <div>
                   {/** HTTPS permite fallback para a versão web quando o app não estiver instalado. */}
                   {(() => {
                     const wazeUrl = buildWazeNavigationUrl(order.address);
                     return <>
                   <p className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-1 flex items-center gap-1"><MapPin className="w-3.5 h-3.5"/> Endereço</p>
                   <p className="text-sm text-zinc-700">{order.address}</p>
                   {wazeUrl && <a
                     href={wazeUrl}
                     target="_blank"
                     rel="noopener noreferrer"
                     className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 mt-2 hover:underline"
                   >
                     Abrir no Waze
                   </a>}
                     </>;
                   })()}
                </div>

                <div>
                   <p className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-2">Itens</p>
                   <ul className="space-y-1.5">
                     {order.items.map((item, idx) => (
                       <li key={idx} className="flex justify-between text-sm text-zinc-700">
                         <span><span className="font-medium text-zinc-900">{item.quantity}x</span> {item.name}</span>
                       </li>
                     ))}
                   </ul>
                </div>

                <div className="pt-3 border-t border-zinc-100 flex justify-between items-center">
                   <span className="text-sm font-medium text-zinc-500">Total</span>
                   <span className="text-lg font-bold text-zinc-900 flex items-center"><DollarSign className="w-4 h-4"/>{order.total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                </div>
              </div>

              {order.status === 'pending' && (
                <div className="p-4 bg-zinc-50 border-t border-zinc-100">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleReject(order.id)}
                      className="flex-1 py-2.5 bg-red-100 hover:bg-red-200 text-red-700 font-medium rounded-lg shadow-sm transition-colors cursor-pointer"
                    >
                      Recusar
                    </button>
                    <button
                      onClick={() => handleAccept(order.id)}
                      className="flex-[2] py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <Check className="w-4 h-4" />
                      Aceitar Pedido
                    </button>
                  </div>
                </div>
              )}
              {order.status === 'accepted' && (
                <div className="p-4 bg-zinc-50 border-t border-zinc-100">
                  <button onClick={() => handleStatusChange(order.id, 'ready_for_delivery')} className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors cursor-pointer">
                    Marcar pronto para entrega
                  </button>
                </div>
              )}
              {order.status === 'ready_for_delivery' && (
                <div className="p-4 bg-zinc-50 border-t border-zinc-100">
                  <button onClick={() => handleStatusChange(order.id, 'out_for_delivery')} className="w-full py-2.5 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-lg shadow-sm transition-colors cursor-pointer">
                    Marcar saiu para entrega
                  </button>
                </div>
              )}
              {order.status === 'out_for_delivery' && (
                <div className="p-4 bg-zinc-50 border-t border-zinc-100">
                  <button onClick={() => handleStatusChange(order.id, 'delivered')} className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg shadow-sm transition-colors cursor-pointer">
                    Marcar como entregue
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

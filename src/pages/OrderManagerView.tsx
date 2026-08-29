import { useState, useEffect, useRef } from 'react';
import { ShoppingBag, Check, MapPin, DollarSign, Clock } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Documentation-Driven Testing:
 * O comportamento esperado para OrderManagerView.tsx:
 * - `useOrdersSSE`: Conecta via EventSource à `/api/v1/orders/events`. Recebe eventos `new_order`.
 * - `Card de Pedido`: Exibe detalhes do pedido (nome, valor, endereço, itens).
 * - `Botão Aceitar`: Para o loop de áudio e atualiza o status do pedido localmente ou via API.
 * - `Link Waze`: Abre a URL `https://waze.com/ul?q=endereco_encode` em nova aba.
 * - `Áudio TTS`: Toca em loop "Olá..." a cada 15s até aceitar o pedido.
 */

// API Base URL (adjust for testing/prod)
import { API_BASE } from "../services/api";

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
  status: 'pending' | 'accepted' | 'completed' | 'cancelled';
  createdAt: string;
}

// Custom Hook for SSE Orders
function useOrdersSSE() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [announcedOrderIds, setAnnouncedOrderIds] = useState<Set<string>>(new Set());
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      setConnectionStatus('connecting');
      try {
        const token = localStorage.getItem('admin_token');
        fetch(`${API_BASE}/orders?token=${encodeURIComponent(token || '')}`)
          .then(response => {
            if (!response.ok) throw new Error('Falha ao carregar pedidos persistidos');
            return response.json();
          })
          .then(data => {
            if (Array.isArray(data.orders)) {
              setOrders(prev => {
                const byId = new Map<string, Order>(data.orders.map((order: Order) => [order.id, order] as [string, Order]));
                prev.forEach(order => byId.set(order.id, order));
                return Array.from(byId.values());
              });
            }
          })
          .catch(error => console.error('Erro ao carregar pedidos persistidos:', error));
        // Usar EventSource nativo ou polyfill dependendo da necessidade de auth (EventSource nativo não suporta headers, então podemos precisar enviar token via query string se aplicável)
        // Por simplicidade na simulação:
        eventSource = new EventSource(`${API_BASE}/orders/events?token=${token}`);

        eventSource.onopen = () => {
          setConnectionStatus('connected');
          console.log('SSE Orders connected');
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'new_order' && data.order) {
              setAnnouncedOrderIds(prev => new Set(prev).add(data.order.id));
              setOrders(prev => prev.some(order => order.id === data.order.id) ? prev : [data.order, ...prev]);
            } else if (data.event === 'order_updated' && data.order) {
              setOrders(prev => prev.map(order => order.id === data.order.id ? data.order : order));
            }
          } catch (e) {
            console.error('Error parsing SSE event:', e);
          }
        };

        eventSource.onerror = (error) => {
          console.error('SSE Error:', error);
          setConnectionStatus('disconnected');
          eventSource?.close();
          // Try to reconnect after 5s
          reconnectTimeout = setTimeout(connect, 5000);
        };
      } catch (error) {
        console.error('Failed to initialize SSE:', error);
        setConnectionStatus('disconnected');
      }
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  return { orders, setOrders, announcedOrderIds, connectionStatus };
}

export default function OrderManagerView() {
  const { orders, setOrders, announcedOrderIds, connectionStatus } = useOrdersSSE();
  const activeAlarms = useRef<{ [orderId: string]: { audio?: HTMLAudioElement, interval?: any } }>({});

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
    const token = localStorage.getItem('admin_token');
    const audioUrl = `${API_BASE}/orders/${encodeURIComponent(order.id)}/tts-alarm?token=${encodeURIComponent(token || '')}`;
    const audio = new Audio(audioUrl);
    
    const playNext = () => {
      audio.play().catch(e => console.error("Erro ao tocar alarme neural:", e));
    };

    audio.onended = () => {
      // Repete o alarme após 10 segundos de silêncio
      const interval = setTimeout(playNext, 10000) as any;
      if (activeAlarms.current[order.id]) {
         activeAlarms.current[order.id].interval = interval;
      }
    };

    playNext();
    activeAlarms.current[order.id] = { audio };
  };

  const stopAlarm = (orderId: string) => {
    const alarm = activeAlarms.current[orderId] as any;
    if (alarm) {
      if (alarm.interval) clearTimeout(alarm.interval);
      if (alarm.audio) {
        alarm.audio.pause();
        alarm.audio.currentTime = 0;
      }
      delete activeAlarms.current[orderId];
    }
  };

  // Cleanup all on unmount
  useEffect(() => {
    return () => {
      Object.keys(activeAlarms.current).forEach(stopAlarm);
    };
  }, []);

  const handleAccept = async (orderId: string) => {
    stopAlarm(orderId);
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch(`${API_BASE}/orders/${encodeURIComponent(orderId)}/accept?token=${encodeURIComponent(token || '')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error('Falha ao confirmar pedido');
      const data = await response.json();
      setOrders(prev => prev.map(o => o.id === orderId ? data.order : o));
      toast.success('Pedido aceito com sucesso!');
    } catch {
      toast.error('Não foi possível confirmar o pedido.');
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
                   {order.status === 'pending' ? 'Pendente' : order.status === 'accepted' ? 'Aceito' : order.status}
                 </span>
              </div>

              <div className="p-4 space-y-4">
                <div>
                   <p className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-1">Cliente</p>
                   <p className="font-medium text-zinc-900">{order.customerName}</p>
                </div>

                <div>
                   <p className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-1 flex items-center gap-1"><MapPin className="w-3.5 h-3.5"/> Endereço</p>
                   <p className="text-sm text-zinc-700">{order.address}</p>
                   <a
                     href={`https://waze.com/ul?q=${encodeURIComponent(order.address)}`}
                     target="_blank"
                     rel="noopener noreferrer"
                     className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 mt-2 hover:underline"
                   >
                     Abrir no Waze
                   </a>
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
                  <button
                    onClick={() => handleAccept(order.id)}
                    className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Check className="w-4 h-4" />
                    Aceitar Pedido
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

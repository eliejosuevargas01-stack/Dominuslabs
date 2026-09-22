import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  ShoppingBag, 
  Check, 
  MapPin, 
  Clock, 
  ExternalLink,
  Flame,
  Archive,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Search,
  ArrowRight,
  ChefHat,
  AlertCircle,
  LayoutGrid,
  Columns3,
  List
} from 'lucide-react';
import { toast } from 'sonner';

/**
 * Documentation-Driven Testing:
 * O comportamento esperado para OrderManagerView.tsx:
 * - `useOrdersWebSocket`: Conecta via WebSocket / SSE à `/api/v1/orders/events`. Recebe eventos `new_order` e `order_updated`.
 * - `Card de Pedido`: Exibe detalhes do pedido (nome, valor, endereço, itens).
 * - `Botão Aceitar`: Para o loop de áudio e atualiza o status do pedido localmente ou via API.
 * - `Link Waze`: Abre uma rota de navegação HTTPS com endereço codificado.
 * - `Áudio TTS`: Toca em loop "Olá..." a cada 15s até aceitar o pedido.
 * - `Abas Operacionais`: Alternância fluida entre 'Operação Ativa' (Novos + Em Preparo) e 'Histórico & Finalizados'.
 */

// API Base URL (adjust for testing/prod)
import { 
  API_BASE, 
  fetchWithAuth 
} from "../services/api";
import { SSEClient } from "../services/sseClient";

interface OrderItem {
  name: string;
  quantity: number;
}

interface Order {
  id: string;
  customerName: string;
  total: number;
  total_amount?: number;
  address: string;
  items: OrderItem[];
  status: 'pending' | 'accepted' | 'ready_for_delivery' | 'out_for_delivery' | 'delivered' | 'completed' | 'cancelled' | 'rejected';
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

function getOrderStatusBadgeClass(status: string): string {
  const normalized = (status || '').toLowerCase();
  if (['delivered', 'completed', 'entregue', 'concluido'].includes(normalized)) {
    return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  }
  if (['rejected', 'cancelled', 'recusado', 'cancelado'].includes(normalized)) {
    return 'bg-rose-50 text-rose-700 border-rose-200';
  }
  if (['pending', 'em_preparo', 'aberto', 'pendente'].includes(normalized)) {
    return 'bg-amber-50 text-amber-700 border-amber-200';
  }
  if (['accepted', 'aceito', 'ready_for_delivery', 'out_for_delivery'].includes(normalized)) {
    return 'bg-blue-50 text-blue-700 border-blue-200';
  }
  return 'bg-zinc-100 text-zinc-600 border-zinc-200';
}

// Custom Hook for real-time Orders
function useOrdersWebSocket() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [announcedOrderIds, setAnnouncedOrderIds] = useState<Set<string>>(new Set());
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    let sseClient: SSEClient | null = null;
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
      setConnectionStatus('connecting');

      sseClient = new SSEClient({
        url: `${API_BASE}/orders/events`,
        onOpen: () => {
          if (!disposed) setConnectionStatus('connected');
        },
        onClose: () => {
          if (!disposed) setConnectionStatus('disconnected');
        },
        onError: () => {
          if (!disposed) setConnectionStatus('disconnected');
        },
        onMessage: (data) => {
          if (!data) return;
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
        }
      });
      sseClient.connect();
    };

    const handleTokenRefreshed = () => {
      if (disposed) return;
      console.log('[OrderManager] Token renovado detectado por evento global. Reconectando...');
      sseClient?.disconnect();
      connect();
    };

    window.addEventListener('token_refreshed', handleTokenRefreshed);

    fetchOrders();
    pollingTimer = setInterval(fetchOrders, 30000); // 30s reconciliation polling
    connect();

    return () => {
      disposed = true;
      window.removeEventListener('token_refreshed', handleTokenRefreshed);
      if (pollingTimer) clearInterval(pollingTimer);
      sseClient?.disconnect();
    };
  }, []);

  return { orders, setOrders, announcedOrderIds, connectionStatus };
}

export default function OrderManagerView() {
  const { orders, setOrders, announcedOrderIds, connectionStatus } = useOrdersWebSocket();
  const activeAlarms = useRef<Record<string, ActiveAlarm>>({});

  // Abas operacionais: 'active' (em operação) vs 'history' (finalizados)
  const [activeTab, setActiveTab] = useState<'active' | 'history'>('active');

  // Filtros de busca na aba de histórico
  const [historySearch, setHistorySearch] = useState<string>('');
  const [historyStatusFilter, setHistoryStatusFilter] = useState<'all' | 'delivered' | 'cancelled'>('all');
  
  // View mode toggle: 'cards' (default), 'kanban', 'list'
  const [viewMode, setViewMode] = useState<'cards' | 'kanban' | 'list'>('cards');

  // Manual order modal state
  const [isManualOrderModalOpen, setIsManualOrderModalOpen] = useState(false);
  const [manualOrderCustomerName, setManualOrderCustomerName] = useState('');
  const [manualOrderAddress, setManualOrderAddress] = useState('');
  const [manualOrderItems, setManualOrderItems] = useState<{id: string; name: string; quantity: number; price: string; notes: string}[]>([
    { id: '1', name: '', quantity: 1, price: '0.00', notes: '' }
  ]);

  // Calculate total for manual order
  const calculateManualOrderTotal = () => {
    return manualOrderItems.reduce((sum, item) => {
      const price = parseFloat(item.price) || 0;
      return sum + price * item.quantity;
    }, 0);
  };

  // Handle adding a new item row
  const addManualOrderItem = () => {
    setManualOrderItems(prev => [
      ...prev,
      { id: Date.now().toString(), name: '', quantity: 1, price: '0.00', notes: '' }
    ]);
  };

  // Handle removing an item
  const removeManualOrderItem = (id: string) => {
    if (manualOrderItems.length > 1) {
      setManualOrderItems(prev => prev.filter(item => item.id !== id));
    }
  };

  // Handle updating an item
  const updateManualOrderItem = (id: string, field: keyof typeof manualOrderItems[0], value: string | number) => {
    setManualOrderItems(prev => prev.map(item => 
      item.id === id ? { ...item, [field]: value } : item
    ));
  };

  // Handle submitting manual order
  const handleCreateManualOrder = async () => {
    if (!manualOrderCustomerName.trim() || !manualOrderAddress.trim()) {
      toast.error('Por favor, preencha o nome do cliente e o endereço.');
      return;
    }
    
    const itemsWithValidData = manualOrderItems.filter(item => item.name.trim());
    if (itemsWithValidData.length === 0) {
      toast.error('Adicione pelo menos um item ao pedido.');
      return;
    }

    const payload = {
      customer_name: manualOrderCustomerName,
      address: manualOrderAddress,
      items: itemsWithValidData.map(item => ({
        nome: item.name,
        quantidade: item.quantity,
        preco_unitario: parseFloat(item.price) || 0,
        observacoes: item.notes
      }))
    };

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        toast.error('Não autenticado. Faça login novamente.');
        return;
      }

      const response = await fetch(`${API_BASE}/orders/manual`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Falha ao criar pedido');
      }

      await response.json();
      toast.success('Pedido criado com sucesso!');
      setIsManualOrderModalOpen(false);
      setManualOrderCustomerName('');
      setManualOrderAddress('');
      setManualOrderItems([{ id: '1', name: '', quantity: 1, price: '0.00', notes: '' }]);
    } catch (error) {
      console.error('Erro ao criar pedido:', error);
      toast.error(error instanceof Error ? error.message : 'Não foi possível criar o pedido.');
    }
  };
  const announceAudioFallback = useCallback((order: Order) => {
    const message = `Novo pedido pendente ${order.id}. Ative o som desta tela.`;
    toast.error(message);
    if ('speechSynthesis' in window && 'SpeechSynthesisUtterance' in window) {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(message));
    }
  }, []);

  const stopAlarm = useCallback((orderId: string) => {
    const alarm = activeAlarms.current[orderId];
    if (!alarm) return;

    delete activeAlarms.current[orderId];
    alarm.abortController.abort();
    if (alarm.interval) clearTimeout(alarm.interval);
    alarm.audio.onended = null;
    alarm.audio.pause();
    alarm.audio.currentTime = 0;
    if (alarm.blobUrl) URL.revokeObjectURL(alarm.blobUrl);
  }, []);

  const playAlarm = useCallback((order: Order) => {
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
  }, [announceAudioFallback]);

  useEffect(() => {
    // Check for new pending orders and start alarm
    orders.forEach(order => {
      if (order.status === 'pending' && announcedOrderIds.has(order.id) && !activeAlarms.current[order.id]) {
        playAlarm(order);
      }
    });

    // Cleanup alarms for non-pending orders
    Object.keys(activeAlarms.current).forEach(orderId => {
      const order = orders.find(o => o.id === orderId);
      if (!order || order.status !== 'pending') {
        stopAlarm(orderId);
      }
    });

  }, [orders, announcedOrderIds, playAlarm, stopAlarm]);

  // Cleanup all on unmount
  useEffect(() => {
    const alarms = activeAlarms.current;
    return () => {
      Object.keys(alarms).forEach(orderId => {
        const alarm = alarms[orderId];
        if (alarm) {
          delete alarms[orderId];
          alarm.abortController.abort();
          if (alarm.interval) clearTimeout(alarm.interval);
          alarm.audio.onended = null;
          alarm.audio.pause();
          alarm.audio.currentTime = 0;
          if (alarm.blobUrl) URL.revokeObjectURL(alarm.blobUrl);
        }
      });
    };
  }, []);

  const handleAccept = useCallback(async (orderId: string) => {
    stopAlarm(orderId);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
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
  }, [stopAlarm]);

  const handleReject = useCallback(async (orderId: string) => {
    stopAlarm(orderId);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
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
  }, [stopAlarm]);

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

  // 1. Particionamento de Ordens
  const incomingOrders = orders.filter(o => o.status === 'pending');
  const inProgressOrders = orders.filter(o => ['accepted', 'ready_for_delivery', 'out_for_delivery'].includes(o.status));
  const finalizedOrders = orders.filter(o => ['delivered', 'completed', 'rejected', 'cancelled'].includes(o.status));
  const activeOrders = [...incomingOrders, ...inProgressOrders];

  // Métricas do Turno
  const deliveredOrders = finalizedOrders.filter(o => ['delivered', 'completed'].includes(o.status));
  const rejectedOrders = finalizedOrders.filter(o => ['rejected', 'cancelled'].includes(o.status));
  const faturamentoConcluido = deliveredOrders.reduce((sum, o) => {
    const val = Number(o.total_amount ?? o.total ?? 0);
    return sum + (isNaN(val) ? 0 : val);
  }, 0);

  // Filtro de Histórico
  const filteredFinalizedOrders = finalizedOrders.filter(order => {
    const query = historySearch.toLowerCase().trim();
    const matchesSearch = !query || 
      order.id.toLowerCase().includes(query) ||
      order.customerName.toLowerCase().includes(query) ||
      order.address.toLowerCase().includes(query) ||
      order.items.some(item => item.name.toLowerCase().includes(query));

    if (!matchesSearch) return false;

    if (historyStatusFilter === 'delivered') {
      return ['delivered', 'completed'].includes(order.status);
    }
    if (historyStatusFilter === 'cancelled') {
      return ['rejected', 'cancelled'].includes(order.status);
    }
    return true;
  });

  // Renderizador do Card Individual de Pedido Operacional
  const renderOperationalCard = (order: Order, isIncoming: boolean) => {
    const wazeUrl = buildWazeNavigationUrl(order.address);

    return (
      <div
        key={order.id}
        className={`bg-white rounded-2xl border transition-all overflow-hidden ${
          isIncoming
            ? 'border-amber-300 shadow-md ring-2 ring-amber-100'
            : 'border-zinc-200 shadow-sm hover:border-zinc-300'
        }`}
      >
        {/* Card Header */}
        <div className={`p-4 border-b flex justify-between items-start ${
          isIncoming ? 'bg-amber-50/60' : 'bg-zinc-50/60'
        }`}>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base text-zinc-900">
                Pedido <span>#{order.id.slice(0, 6).toUpperCase()}</span>
              </span>
              {isIncoming && (
                <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md bg-amber-500 text-white animate-pulse">
                  Novo
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-zinc-500 text-xs mt-1">
              <Clock className="w-3.5 h-3.5 text-zinc-400" />
              <span>{new Date(order.createdAt).toLocaleTimeString()}</span>
            </div>
          </div>
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${getOrderStatusBadgeClass(order.status)}`}>
            {statusLabels[order.status] || order.status}
          </span>
        </div>

        {/* Card Body */}
        <div className="p-4 space-y-3.5 text-sm">
          <div>
            <p className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-0.5">Cliente</p>
            <p className="font-semibold text-zinc-900">{order.customerName}</p>
          </div>

          <div>
            <p className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-0.5 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-zinc-400" /> Endereço
            </p>
            <p className="text-xs text-zinc-600 leading-relaxed">{order.address}</p>
            {wazeUrl && (
              <a
                href={wazeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 font-medium hover:underline flex items-center gap-1 text-xs mt-1.5 inline-flex"
              >
                <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                <span>Abrir no Waze</span>
              </a>
            )}
          </div>

          <div>
            <p className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5">Itens do Pedido</p>
            <ul className="space-y-1 bg-zinc-50 p-2.5 rounded-xl border border-zinc-100">
              {order.items.map((item, idx) => (
                <li key={idx} className="flex justify-between text-xs text-zinc-700">
                  <span>
                    <span className="font-bold text-zinc-900">{item.quantity}x</span> {item.name}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="pt-2 border-t border-zinc-100 flex justify-between items-center">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Total</span>
            <span className="text-base font-extrabold text-zinc-900">
              R$ {Number(order.total_amount || order.total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        {/* Card Actions */}
        <div className="p-3.5 bg-zinc-50/80 border-t border-zinc-100">
          {order.status === 'pending' && (
            <div className="flex gap-2">
              <button
                onClick={() => handleReject(order.id)}
                className="flex-1 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs rounded-xl border border-rose-200 transition-colors cursor-pointer"
              >
                Recusar
              </button>
              <button
                onClick={() => handleAccept(order.id)}
                className="flex-[2] py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Check className="w-3.5 h-3.5" />
                Aceitar Pedido
              </button>
            </div>
          )}
          {order.status === 'accepted' && (
            <button 
              onClick={() => handleStatusChange(order.id, 'ready_for_delivery')} 
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-sm transition-colors cursor-pointer"
            >
              Marcar Pronto para Entrega
            </button>
          )}
          {order.status === 'ready_for_delivery' && (
            <button 
              onClick={() => handleStatusChange(order.id, 'out_for_delivery')} 
              className="w-full py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-sm transition-colors cursor-pointer"
            >
              Marcar Saiu para Entrega
            </button>
          )}
          {order.status === 'out_for_delivery' && (
            <button 
              onClick={() => handleStatusChange(order.id, 'delivered')} 
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition-colors cursor-pointer"
            >
              Marcar como Entregue
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-zinc-50">
      {/* Header Principal com Status de Conexão */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <ShoppingBag className="w-7 h-7 text-purple-600" />
            Order Manager (PDV)
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Painel operacional para gestão em tempo real de pedidos e entregas.
          </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsManualOrderModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-xl shadow-sm transition-all"
          >
            <ShoppingBag className="w-4 h-4" />
            <span>+ Novo Pedido</span>
          </button>
        </div>
        </div>
        <div className="flex items-center gap-2 text-xs bg-white border border-zinc-200 px-3.5 py-1.5 rounded-full shadow-sm self-start sm:self-auto">
           <span className={`w-2 h-2 rounded-full ${connectionStatus === 'connected' ? 'bg-emerald-500 animate-pulse' : connectionStatus === 'connecting' ? 'bg-amber-500' : 'bg-rose-500'}`}></span>
           <span className="text-zinc-600 font-semibold">
             {connectionStatus === 'connected' ? 'Conectado (Ao Vivo)' : connectionStatus === 'connecting' ? 'Conectando...' : 'Desconectado'}
           </span>
        </div>
      </div>

      {/* Navegação de Abas Operacionais */}
      <div className="flex items-center justify-between gap-4 border-b border-zinc-200 pb-3 mb-6">
        <div role="tablist" aria-label="Abas operacionais do PDV" className="flex items-center gap-2 bg-zinc-100 p-1 rounded-2xl border border-zinc-200/80">
          <button
            role="tab"
            aria-selected={activeTab === 'active'}
            onClick={() => setActiveTab('active')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'active'
                ? 'bg-white text-purple-700 shadow-sm'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            <Flame className="w-4 h-4 text-amber-500" />
            <span>Operação Ativa</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-black ${
              activeOrders.length > 0 ? 'bg-amber-100 text-amber-800' : 'bg-zinc-200 text-zinc-600'
            }`}>
              {activeOrders.length}
            </span>
          </button>

          <button
            aria-label="Histórico & Finalizados"
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'history'
                ? 'bg-white text-purple-700 shadow-sm'
                : 'text-zinc-600 hover:text-zinc-900'
            }`}
          >
            <Archive className="w-4 h-4 text-purple-600" />
            <span>Histórico & Finalizados</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-zinc-200 text-zinc-600">
              {finalizedOrders.length}
            </span>
          </button>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-500">Visão:</span>
          <div className="flex items-center bg-zinc-100 p-0.5 rounded-xl border border-zinc-200">
            <button
              onClick={() => setViewMode('cards')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${viewMode === 'cards' ? 'bg-white text-purple-700 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'}`}
            >
              <LayoutGrid className="w-4 h-4" />
              <span className="hidden sm:inline">Cards</span>
            </button>
            <button
              onClick={() => setViewMode('kanban')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${viewMode === 'kanban' ? 'bg-white text-purple-700 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'}`}
            >
              <Columns3 className="w-4 h-4" />
              <span className="hidden sm:inline">Kanban</span>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${viewMode === 'list' ? 'bg-white text-purple-700 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'}`}
            >
              <List className="w-4 h-4" />
              <span className="hidden sm:inline">Lista</span>
            </button>
          </div>
        </div>
        </div>

        {/* Resumo Rápido no Topo */}
        <div className="hidden sm:flex items-center gap-3 text-xs font-semibold text-zinc-500">
          <span>{incomingOrders.length} pendentes</span>
          <span className="text-zinc-300">•</span>
          <span>{inProgressOrders.length} em rota/preparo</span>
        </div>
      </div>

      {/* Conteúdo da Aba 1: Operação Ativa */}
      {activeTab === 'active' && (
        <div role="tabpanel" aria-label="Operação Ativa" className="flex flex-col flex-1 pb-12">
                    {viewMode === 'kanban' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 flex-1 min-h-0">
              {/* Pendente */}
              <div className="flex flex-col gap-3 bg-white border border-zinc-200 rounded-2xl p-3 min-h-0">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <Flame className="w-4 h-4 text-amber-600" />
                    <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wider">Pendente</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-100 text-amber-800">
                    {incomingOrders.length}
                  </span>
                </div>
                <div className="space-y-3 overflow-y-auto">
                  {incomingOrders.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center text-zinc-400">
                      <Clock className="w-8 h-8 mb-2" />
                      <span className="text-xs">Nenhum pedido pendente</span>
                    </div>
                  ) : (
                    incomingOrders.map(order => renderOperationalCard(order, true))
                  )}
                </div>
              </div>

              {/* Aceito */}
              <div className="flex flex-col gap-3 bg-white border border-zinc-200 rounded-2xl p-3 min-h-0">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-blue-600" />
                    <h3 className="text-xs font-bold text-blue-900 uppercase tracking-wider">Aceito</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-blue-100 text-blue-800">
                    {incomingOrders.filter(o => o.status === 'accepted').length + inProgressOrders.filter(o => o.status === 'accepted').length}
                  </span>
                </div>
                <div className="space-y-3 overflow-y-auto">
                  {[...incomingOrders, ...inProgressOrders].filter(o => o.status === 'accepted').length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center text-zinc-400">
                      <Check className="w-8 h-8 mb-2" />
                      <span className="text-xs">Nenhum pedido aceito</span>
                    </div>
                  ) : (
                    [...incomingOrders, ...inProgressOrders].filter(o => o.status === 'accepted').map(order => (
                      <div key={order.id} className="bg-zinc-50 p-3 rounded-xl border border-zinc-100">
                        {renderOperationalCard(order, false)}
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Pronto para Entrega */}
              <div className="flex flex-col gap-3 bg-white border border-zinc-200 rounded-2xl p-3 min-h-0">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-purple-600" />
                    <h3 className="text-xs font-bold text-purple-900 uppercase tracking-wider">Pronto</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-purple-100 text-purple-800">
                    {inProgressOrders.filter(o => o.status === 'ready_for_delivery').length}
                  </span>
                </div>
                <div className="space-y-3 overflow-y-auto">
                  {inProgressOrders.filter(o => o.status === 'ready_for_delivery').length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center text-zinc-400">
                      <ChefHat className="w-8 h-8 mb-2" />
                      <span className="text-xs">Nenhum pedido pronto</span>
                    </div>
                  ) : (
                    inProgressOrders.filter(o => o.status === 'ready_for_delivery').map(order => (
                      <div key={order.id} className="bg-zinc-50 p-3 rounded-xl border border-zinc-100">
                        {renderOperationalCard(order, false)}
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Saiu para Entrega */}
              <div className="flex flex-col gap-3 bg-white border border-zinc-200 rounded-2xl p-3 min-h-0">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-amber-600" />
                    <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wider">Saiu</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-100 text-amber-800">
                    {inProgressOrders.filter(o => o.status === 'out_for_delivery').length}
                  </span>
                </div>
                <div className="space-y-3 overflow-y-auto">
                  {inProgressOrders.filter(o => o.status === 'out_for_delivery').length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center text-zinc-400">
                      <ExternalLink className="w-8 h-8 mb-2" />
                      <span className="text-xs">Nenhum pedido em rota</span>
                    </div>
                  ) : (
                    inProgressOrders.filter(o => o.status === 'out_for_delivery').map(order => (
                      <div key={order.id} className="bg-zinc-50 p-3 rounded-xl border border-zinc-100">
                        {renderOperationalCard(order, false)}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

                    {viewMode === 'list' && (
            <div className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-200 text-[11px] font-bold text-zinc-600 uppercase tracking-wider bg-zinc-50/50">
                      <th className="py-3 px-5">ID</th>
                      <th className="py-3 px-5">Cliente</th>
                      <th className="py-3 px-5">Endereço</th>
                      <th className="py-3 px-5">Itens</th>
                      <th className="py-3 px-5">Total</th>
                      <th className="py-3 px-5">Status</th>
                      <th className="py-3 px-5 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 text-xs">
                    {[...incomingOrders, ...inProgressOrders].length > 0 ? (
                      [...incomingOrders, ...inProgressOrders].map((order) => (
                        <tr key={order.id} className="hover:bg-zinc-50 transition-colors">
                          <td className="py-3.5 px-5 font-bold text-zinc-900">#{order.id.slice(0, 6).toUpperCase()}</td>
                          <td className="py-3.5 px-5 font-semibold text-zinc-900">{order.customerName}</td>
                          <td className="py-3.5 px-5 text-zinc-600 max-w-xs truncate">{order.address}</td>
                          <td className="py-3.5 px-5 text-zinc-600 max-w-xs">
                            <div className="truncate">{order.items.slice(0, 3).map(i => `${i.quantity}x ${i.name}`).join(', ')}</div>
                            {order.items.length > 3 && <span className="text-zinc-400 text-[10px]">+{order.items.length - 3} itens</span>}
                          </td>
                          <td className="py-3.5 px-5 font-bold text-zinc-900">
                            R$ {Number(order.total_amount || order.total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="py-3.5 px-5">
                            <span className={`px-2.5 py-1 text-[11px] font-semibold rounded-full border ${getOrderStatusBadgeClass(order.status)}`}>
                              {statusLabels[order.status] || order.status}
                            </span>
                          </td>
                          <td className="py-3.5 px-5 text-right">
                            {order.status === 'pending' && (
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  // eslint-disable-next-line react-hooks/refs
                                  onClick={() => handleReject(order.id)}
                                  className="text-xs font-bold text-rose-600 hover:text-rose-700 px-2 py-1 rounded hover:bg-rose-50"
                                >
                                  Recusar
                                </button>
                                <button
                                  onClick={() => handleAccept(order.id)}
                                  className="text-xs font-bold text-purple-600 hover:text-purple-700 px-2 py-1 rounded bg-purple-50 hover:bg-purple-100"
                                >
                                  Aceitar
                                </button>
                              </div>
                            )}
                            {order.status === 'accepted' && (
                              <button
                                onClick={() => handleStatusChange(order.id, 'ready_for_delivery')}
                                className="text-xs font-bold text-blue-600 hover:text-blue-700 px-2 py-1 rounded bg-blue-50 hover:bg-blue-100"
                              >
                                Marcar Pronto
                              </button>
                            )}
                            {order.status === 'ready_for_delivery' && (
                              <button
                                onClick={() => handleStatusChange(order.id, 'out_for_delivery')}
                                className="text-xs font-bold text-amber-600 hover:text-amber-700 px-2 py-1 rounded bg-amber-50 hover:bg-amber-100"
                              >
                                Marcar Saiu
                              </button>
                            )}
                            {order.status === 'out_for_delivery' && (
                              <button
                                onClick={() => handleStatusChange(order.id, 'delivered')}
                                className="text-xs font-bold text-emerald-600 hover:text-emerald-700 px-2 py-1 rounded bg-emerald-50 hover:bg-emerald-100"
                              >
                                Entregue
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-zinc-400">
                          <Clock className="w-6 h-6 mx-auto mb-2 text-zinc-300" />
                          <span className="text-sm font-medium">Nenhum pedido ativo</span>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

                    {viewMode === 'cards' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
              {/* Coluna 1: Novos & Entrantes */}
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between bg-amber-50/80 border border-amber-200/70 p-3.5 rounded-2xl">
                  <div className="flex items-center gap-2">
                    <Flame className="w-5 h-5 text-amber-600" />
                    <h2 className="text-sm font-bold text-amber-900">Novos & Entrantes</h2>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-amber-200/70 text-amber-900">
                    {incomingOrders.length}
                  </span>
                </div>

                <div className="space-y-4 flex-1">
                  {incomingOrders.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-10 text-center bg-white border border-dashed border-zinc-200 rounded-2xl min-h-[220px]">
                      <Clock className="w-10 h-10 text-zinc-300 mb-2" />
                      <p className="text-sm font-bold text-zinc-700">Nenhum pedido novo no momento</p>
                      <p className="text-xs text-zinc-400 mt-0.5">Aguardando entradas e alertas neurais...</p>
                    </div>
                  ) : (
                    incomingOrders.map(order => renderOperationalCard(order, true))
                  )}
                </div>
              </div>

              {/* Coluna 2: Em Preparo & Rota */}
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between bg-blue-50/80 border border-blue-200/70 p-3.5 rounded-2xl">
                  <div className="flex items-center gap-2">
                    <ChefHat className="w-5 h-5 text-blue-600" />
                    <h2 className="text-sm font-bold text-blue-900">Em Preparo & Rota</h2>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-blue-200/70 text-blue-900">
                    {inProgressOrders.length}
                  </span>
                </div>

                <div className="space-y-4 flex-1">
                  {inProgressOrders.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-10 text-center bg-white border border-dashed border-zinc-200 rounded-2xl min-h-[220px]">
                      <ShoppingBag className="w-10 h-10 text-zinc-300 mb-2" />
                      <p className="text-sm font-bold text-zinc-700">Nenhum pedido em preparo ou rota</p>
                      <p className="text-xs text-zinc-400 mt-0.5">Os pedidos aceitos aparecerão listados aqui.</p>
                    </div>
                  ) : (
                    inProgressOrders.map(order => renderOperationalCard(order, false))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Gaveta / Barra Minimizada de Finalizados no Rodapé da Visão Ativa */}
          <div className="mt-8 bg-white border border-zinc-200 rounded-2xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-zinc-900">
                  Resumo do Turno: {deliveredOrders.length} {deliveredOrders.length === 1 ? 'pedido concluído' : 'pedidos concluídos'}
                </h3>
                <p className="text-xs text-zinc-500 font-medium mt-0.5">
                  Faturamento consolidado: <span className="font-bold text-emerald-700">R$ {faturamentoConcluido.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  {rejectedOrders.length > 0 && (
                    <span className="text-zinc-400 ml-2">({rejectedOrders.length} cancelados/recusados)</span>
                  )}
                </p>
              </div>
            </div>

            {/* Mini previews dos últimos finalizados para manter contexto no DOM */}
            {finalizedOrders.length > 0 && (
              <div className="hidden lg:flex items-center gap-2">
                {finalizedOrders.slice(0, 3).map(order => (
                  <span
                    key={order.id}
                    className="flex items-center gap-1.5 bg-zinc-50 px-2 py-1 rounded-lg border border-zinc-200 text-[11px]"
                  >
                    <span className="text-zinc-500 font-medium">#{order.id.slice(0, 6).toUpperCase()}</span>
                    <span className={`px-2 py-0.5 rounded-md border text-[10px] font-semibold ${getOrderStatusBadgeClass(order.status)}`}>
                      {statusLabels[order.status] || order.status}
                    </span>
                    <span className="font-bold text-zinc-700">R$&nbsp;<span className="tabular-nums">{Number(order.total_amount || order.total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></span>
                  </span>
                ))}
                {finalizedOrders.length > 3 && (
                  <span className="text-[11px] text-zinc-400 font-semibold">
                    +{finalizedOrders.length - 3}
                  </span>
                )}
              </div>
            )}

            <button
              onClick={() => setActiveTab('history')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-purple-700 bg-purple-50 hover:bg-purple-100 transition-all cursor-pointer self-stretch md:self-auto justify-center"
            >
              <span>Ver Histórico Completo</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Conteúdo da Aba 2: Histórico & Finalizados */}
      {activeTab === 'history' && (
        <div role="tabpanel" aria-label="Histórico & Finalizados" className="space-y-6 pb-12">
          {/* Cards de Métricas de Fechamento */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="surface-card p-5 border border-emerald-100 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">Pedidos Concluídos</span>
                <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-zinc-900">{deliveredOrders.length}</div>
              <p className="text-[11px] text-emerald-700 font-semibold mt-1">Entregas realizadas com sucesso</p>
            </div>

            <div className="surface-card p-5 border border-rose-100 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">Cancelados / Recusados</span>
                <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                  <XCircle className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-zinc-900">{rejectedOrders.length}</div>
              <p className="text-[11px] text-rose-600 font-semibold mt-1">Não convertidos na operação</p>
            </div>

            <div className="surface-card p-5 border border-purple-100 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">Faturamento Consolidado</span>
                <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-zinc-900">
                R$&nbsp;<span className="tabular-nums">{faturamentoConcluido.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
              <p className="text-[11px] text-purple-700 font-semibold mt-1">Total bruto faturado</p>
            </div>
          </div>

          {/* Filtros e Busca no Histórico */}
          <div className="surface-card p-4 bg-white border border-zinc-200 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                placeholder="Buscar por cliente, ID ou endereço..."
                className="pl-9 pr-3 py-1.5 text-xs rounded-xl border border-zinc-200 focus:border-purple-500 outline-none w-full"
              />
            </div>

            <div className="flex items-center gap-1.5 bg-zinc-100 p-1 rounded-xl border border-zinc-200 text-xs font-bold self-stretch sm:self-auto justify-center">
              <button
                onClick={() => setHistoryStatusFilter('all')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                  historyStatusFilter === 'all' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                Todos ({finalizedOrders.length})
              </button>
              <button
                onClick={() => setHistoryStatusFilter('delivered')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                  historyStatusFilter === 'delivered' ? 'bg-white text-emerald-700 shadow-sm' : 'text-zinc-600 hover:text-emerald-700'
                }`}
              >
                Entregues ({deliveredOrders.length})
              </button>
              <button
                onClick={() => setHistoryStatusFilter('cancelled')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                  historyStatusFilter === 'cancelled' ? 'bg-white text-rose-700 shadow-sm' : 'text-zinc-600 hover:text-rose-700'
                }`}
              >
                Cancelados ({rejectedOrders.length})
              </button>
            </div>
          </div>

          {/* Tabela de Pedidos Finalizados */}
          <div className="surface-card bg-white border border-zinc-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-zinc-200 text-[11px] font-bold text-zinc-600 uppercase tracking-wider bg-zinc-50/50">
                    <th className="py-3 px-5">ID / Horário</th>
                    <th className="py-3 px-5">Cliente</th>
                    <th className="py-3 px-5">Itens Resumidos</th>
                    <th className="py-3 px-5">Endereço</th>
                    <th className="py-3 px-5">Total</th>
                    <th className="py-3 px-5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 text-xs">
                  {filteredFinalizedOrders.length > 0 ? (
                    filteredFinalizedOrders.map((order) => {
                      const wazeUrl = buildWazeNavigationUrl(order.address);

                      return (
                        <tr key={order.id} className="hover:bg-zinc-50 transition-colors">
                          <td className="py-3.5 px-5">
                            <div className="font-bold text-zinc-900">#{order.id.slice(0, 6).toUpperCase()}</div>
                            <div className="text-[11px] text-zinc-400 mt-0.5">
                              {new Date(order.createdAt).toLocaleTimeString()} • {new Date(order.createdAt).toLocaleDateString()}
                            </div>
                          </td>
                          <td className="py-3.5 px-5 font-semibold text-zinc-900">
                            {order.customerName}
                          </td>
                          <td className="py-3.5 px-5 text-zinc-600 max-w-xs">
                            <div className="truncate font-medium">
                              {order.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
                            </div>
                          </td>
                          <td className="py-3.5 px-5 text-zinc-600 max-w-xs">
                            <div className="truncate">{order.address}</div>
                            {wazeUrl && (
                              <a
                                href={wazeUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 font-medium hover:underline inline-flex items-center gap-1 text-[11px] mt-0.5"
                              >
                                <ExternalLink className="w-3 h-3" /> Waze
                              </a>
                            )}
                          </td>
                          <td className="py-3.5 px-5 font-bold text-zinc-900 whitespace-nowrap">
                            R$ {Number(order.total_amount || order.total || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="py-3.5 px-5 whitespace-nowrap">
                            <span className={`px-2.5 py-1 text-[11px] font-semibold rounded-full border ${getOrderStatusBadgeClass(order.status)}`}>
                              {statusLabels[order.status] || order.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-400">
                        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-zinc-300" />
                        <p className="text-sm font-semibold text-zinc-700">Nenhum registro encontrado no histórico</p>
                        <p className="text-xs text-zinc-400 mt-1">Os pedidos finalizados durante a operação aparecerão consolidados nesta listagem.</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Manual Order Modal */}
      {isManualOrderModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl border border-zinc-200 shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-zinc-100 p-4 flex items-center justify-between z-10">
              <h2 className="text-lg font-bold text-zinc-900">Criar Pedido Manual</h2>
              <button
                onClick={() => setIsManualOrderModalOpen(false)}
                className="p-2 text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-5">
              {/* Customer Info */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-zinc-700 uppercase tracking-wider">Nome do Cliente</label>
                <input
                  type="text"
                  value={manualOrderCustomerName}
                  onChange={(e) => setManualOrderCustomerName(e.target.value)}
                  placeholder="Ex: João da Silva"
                  className="w-full px-3 py-2 text-sm rounded-xl border border-zinc-200 focus:border-purple-500 outline-none transition-colors"
                />
              </div>

              {/* Address */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-zinc-700 uppercase tracking-wider">Endereço de Entrega</label>
                <textarea
                  value={manualOrderAddress}
                  onChange={(e) => setManualOrderAddress(e.target.value)}
                  placeholder="Ex: Rua das Flores, 123 - Centro"
                  rows={2}
                  className="w-full px-3 py-2 text-sm rounded-xl border border-zinc-200 focus:border-purple-500 outline-none transition-colors resize-none"
                />
              </div>

              {/* Items List */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-zinc-700 uppercase tracking-wider">Itens do Pedido</label>
                  <button
                    onClick={addManualOrderItem}
                    className="text-xs font-bold text-purple-600 hover:text-purple-700 px-3 py-1 rounded-lg bg-purple-50 hover:bg-purple-100 transition-colors"
                  >
                    + Adicionar Item
                  </button>
                </div>

                <div className="space-y-2">
                  {manualOrderItems.map((item, idx) => (
                    <div key={item.id} className="flex flex-col sm:flex-row gap-2 items-start sm:items-center bg-zinc-50 p-3 rounded-xl border border-zinc-100">
                      <div className="flex-1 space-y-1.5 w-full sm:w-auto">
                        <input
                          type="text"
                          value={item.name}
                          onChange={(e) => updateManualOrderItem(item.id, 'name', e.target.value)}
                          placeholder={`Item ${idx + 1}`}
                          className="w-full sm:w-48 px-2 py-1.5 text-sm rounded-lg border border-zinc-200 focus:border-purple-500 outline-none"
                        />
                        <input
                          type="text"
                          value={item.notes}
                          onChange={(e) => updateManualOrderItem(item.id, 'notes', e.target.value)}
                          placeholder="Observações (opcional)"
                          className="w-full sm:w-64 px-2 py-1.5 text-xs rounded-lg border border-zinc-200 focus:border-purple-500 outline-none text-zinc-500"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="1"
                          value={item.quantity}
                          onChange={(e) => updateManualOrderItem(item.id, 'quantity', parseInt(e.target.value) || 0)}
                          className="w-20 px-2 py-1.5 text-sm rounded-lg border border-zinc-200 focus:border-purple-500 outline-none text-center"
                        />
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.price}
                          onChange={(e) => updateManualOrderItem(item.id, 'price', e.target.value)}
                          placeholder="0.00"
                          className="w-24 px-2 py-1.5 text-sm rounded-lg border border-zinc-200 focus:border-purple-500 outline-none text-right font-medium"
                        />
                        {manualOrderItems.length > 1 && (
                          <button
                            onClick={() => removeManualOrderItem(item.id)}
                            className="px-2 py-1.5 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Total Display */}
                <div className="pt-3 border-t border-zinc-100 flex items-center justify-between">
                  <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Total do Pedido</span>
                  <span className="text-lg font-extrabold text-zinc-900">
                    R$ {calculateManualOrderTotal().toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-white border-t border-zinc-100 p-4 flex items-center justify-end gap-3 z-10 rounded-b-2xl">
              <button
                onClick={() => setIsManualOrderModalOpen(false)}
                className="px-4 py-2 text-xs font-bold text-zinc-600 hover:text-zinc-800 hover:bg-zinc-100 rounded-xl transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreateManualOrder}
                className="px-4 py-2 text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 rounded-xl shadow-sm transition-all flex items-center gap-2"
              >
                <ShoppingBag className="w-4 h-4" />
                <span>Salvar Pedido</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

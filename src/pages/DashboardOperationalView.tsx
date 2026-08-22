import { useState } from 'react';
import {
  ShoppingBag,
  DollarSign,
  TrendingUp,
  Bot,
  UserCheck,
  ArrowUpRight,
  Clock,
  RefreshCw,
  BarChart2,
  Inbox
} from 'lucide-react';

// Types for backend integration
export interface MetricData {
  pedidosHoje: number;
  ticketMedio: number;
  faturamentoDia: number;
  taxaConversao: number; // percentage e.g. 85.5
}

export interface EfficiencyData {
  atendimentosIa: number;
  atendimentosHumanos: number;
  porcentagemIa: number;
}

export interface OrderItem {
  id: string;
  clienteNome: string;
  valorTotal: number;
  status: 'NOVO' | 'EM_PREPARO' | 'CONCLUIDO' | 'CANCELADO';
  tempoAtendimento: string;
  horaPedido: string;
}

interface DashboardOperationalProps {
  metrics?: MetricData;
  efficiency?: EfficiencyData;
  orders?: OrderItem[];
  loading?: boolean;
  onRefresh?: () => void;
}

export default function DashboardOperationalView({
  metrics,
  efficiency,
  orders = [],
  loading = false,
  onRefresh
}: DashboardOperationalProps) {
  const [filterPeriod, setFilterPeriod] = useState<'hoje' | '7d' | '30d'>('hoje');

  // Status Badge Helper
  const getStatusBadge = (status: OrderItem['status']) => {
    switch (status) {
      case 'NOVO':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-blue-50 text-blue-700 border border-blue-200">Novo Pedido</span>;
      case 'EM_PREPARO':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-amber-50 text-amber-700 border border-amber-200">Em Preparo</span>;
      case 'CONCLUIDO':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">Concluído</span>;
      case 'CANCELADO':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-rose-50 text-rose-700 border border-rose-200">Cancelado</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-zinc-100 text-zinc-600">Pendente</span>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Area */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-semibold text-zinc-900 flex items-center gap-2.5">
            <BarChart2 className="w-6 h-6 text-purple-600" />
            Resumo Operacional & Performance
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Métricas de vendas em tempo real, eficiência do atendimento por IA e acompanhamento da fila de pedidos.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Period Filter Dropdown */}
          <div className="flex items-center bg-zinc-100 p-1 rounded-xl border border-zinc-200 text-xs font-semibold">
            <button
              onClick={() => setFilterPeriod('hoje')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${filterPeriod === 'hoje' ? 'bg-white text-zinc-900 shadow-sm font-semibold' : 'text-zinc-500 hover:text-zinc-900 font-medium'}`}
            >
              Hoje
            </button>
            <button
              onClick={() => setFilterPeriod('7d')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${filterPeriod === '7d' ? 'bg-white text-zinc-900 shadow-sm font-semibold' : 'text-zinc-500 hover:text-zinc-900 font-medium'}`}
            >
              7 Dias
            </button>
            <button
              onClick={() => setFilterPeriod('30d')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${filterPeriod === '30d' ? 'bg-white text-zinc-900 shadow-sm font-semibold' : 'text-zinc-500 hover:text-zinc-900 font-medium'}`}
            >
              30 Dias
            </button>
          </div>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-600 hover:text-purple-700 transition-all cursor-pointer shadow-sm disabled:opacity-50"
            title="Atualizar Dados Operacionais"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Cards Superiores (Métricas) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Pedidos Hoje */}
        <div className="surface-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Pedidos Hoje</span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-zinc-900">
            {metrics?.pedidosHoje !== undefined ? metrics.pedidosHoje : '—'}
          </div>
          <p className="text-[11px] text-zinc-400 mt-1.5 flex items-center gap-1 font-medium">
            <Clock className="w-3 h-3" /> Atualizado em tempo real
          </p>
        </div>

        {/* Metric 2: Ticket Médio */}
        <div className="surface-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Ticket Médio</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-zinc-900">
            {metrics?.ticketMedio !== undefined
              ? `R$ ${metrics.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : '—'}
          </div>
          <p className="text-[11px] text-zinc-400 mt-1.5 flex items-center gap-1 font-medium">
            Média por pedido fechado
          </p>
        </div>

        {/* Metric 3: Faturamento do Dia */}
        <div className="surface-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Faturamento Diário</span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-zinc-900">
            {metrics?.faturamentoDia !== undefined
              ? `R$ ${metrics.faturamentoDia.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : '—'}
          </div>
          <p className="text-[11px] text-emerald-600 mt-1.5 flex items-center gap-1 font-semibold">
            <ArrowUpRight className="w-3 h-3" /> Bruto consolidado
          </p>
        </div>

        {/* Metric 4: Taxa de Conversão */}
        <div className="surface-card p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Conversão</span>
            <div className="w-9 h-9 rounded-xl bg-orange-50 flex items-center justify-center text-orange-600">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-zinc-900">
            {metrics?.taxaConversao !== undefined ? `${metrics.taxaConversao.toFixed(1)}%` : '—'}
          </div>
          <p className="text-[11px] text-zinc-400 mt-1.5 font-medium">
            Atendimentos vs. venda
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Gráfico / Container de Eficiência da IA vs Atendimento Humano */}
        <div className="lg:col-span-1 surface-card p-6 flex flex-col justify-between">
          <div className="border-b border-zinc-100 pb-4 mb-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                <Bot className="w-4 h-4 text-purple-600" />
                Eficiência da IA
              </h2>
              {efficiency && (
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                  {efficiency.porcentagemIa}% Auto
                </span>
              )}
            </div>
            <p className="text-xs text-zinc-500 mt-2">
              Resoluções 100% autônomas vs. Transbordos.
            </p>
          </div>

          {/* UI Container */}
          {efficiency ? (
            <div className="space-y-4">
              <div className="flex flex-col gap-2 text-xs font-medium text-zinc-600">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-zinc-900">
                    <span className="w-2 h-2 rounded-full bg-purple-600"></span>
                    IA Resolvidos
                  </span>
                  <span className="font-semibold">{efficiency.atendimentosIa}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-zinc-900">
                    <span className="w-2 h-2 rounded-full bg-zinc-300"></span>
                    Humano
                  </span>
                  <span className="font-semibold">{efficiency.atendimentosHumanos}</span>
                </div>
              </div>

              <div className="w-full h-2.5 bg-zinc-100 rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-purple-600 rounded-full"
                  style={{ width: `${Math.min(Math.max(efficiency.porcentagemIa, 0), 100)}%` }}
                />
                <div
                  className="h-full bg-transparent rounded-full"
                  style={{ width: `${100 - Math.min(Math.max(efficiency.porcentagemIa, 0), 100)}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-10 rounded-xl">
              <Bot className="w-8 h-8 text-zinc-200 mb-2" />
              <p className="text-xs text-zinc-400">Dados indisponíveis</p>
            </div>
          )}
        </div>

        {/* Tabela de Últimos Pedidos */}
        <div className="lg:col-span-2 surface-card overflow-hidden">
          <div className="p-5 border-b border-zinc-100 flex items-center justify-between ">
            <div>
              <h2 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-purple-600" />
                Fila de Pedidos Recentes
              </h2>
            </div>
            <span className="text-[10px] font-semibold text-zinc-500 bg-zinc-100 px-2 py-0.5 rounded-full border border-zinc-200">
              {orders.length} {orders.length === 1 ? 'registro' : 'registros'}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-200 text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                  <th className="py-3 px-5">ID / Hora</th>
                  <th className="py-3 px-5">Cliente</th>
                  <th className="py-3 px-5">Total</th>
                  <th className="py-3 px-5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 text-sm">
                {orders.length > 0 ? (
                  orders.map((pedido) => (
                    <tr key={pedido.id} className="hover:bg-zinc-50 transition-colors">
                      <td className="py-3 px-5">
                        <div className="font-semibold text-zinc-900">#{pedido.id}</div>
                        <div className="text-[11px] text-zinc-500 mt-0.5">{pedido.horaPedido}</div>
                      </td>
                      <td className="py-3 px-5 font-medium text-zinc-800">
                        {pedido.clienteNome}
                      </td>
                      <td className="py-3 px-5 font-semibold text-zinc-900">
                        R$ {pedido.valorTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-5">
                        {getStatusBadge(pedido.status)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-12 text-center">
                      <Inbox className="w-8 h-8 text-zinc-200 mx-auto mb-2" />
                      <p className="text-sm text-zinc-500">Nenhum pedido mapeado na sessão atual.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

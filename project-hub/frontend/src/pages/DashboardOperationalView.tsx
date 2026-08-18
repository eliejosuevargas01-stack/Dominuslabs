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
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-slate-100 text-slate-600">Pendente</span>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header Area */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-6 rounded-2xl border border-violet-100 shadow-sm">
        <div>
          <h1 className="text-2xl font-display font-extrabold text-slate-900 flex items-center gap-2.5">
            <BarChart2 className="w-7 h-7 text-purple-600" />
            Resumo Operacional & Performance
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Métricas de vendas em tempo real, eficiência do atendimento por IA e acompanhamento da fila de pedidos.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Period Filter Dropdown */}
          <div className="flex items-center bg-slate-100/80 p-1 rounded-xl border border-slate-200/60 text-xs font-semibold">
            <button
              onClick={() => setFilterPeriod('hoje')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${filterPeriod === 'hoje' ? 'bg-white text-purple-700 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900'}`}
            >
              Hoje
            </button>
            <button
              onClick={() => setFilterPeriod('7d')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${filterPeriod === '7d' ? 'bg-white text-purple-700 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900'}`}
            >
              7 Dias
            </button>
            <button
              onClick={() => setFilterPeriod('30d')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${filterPeriod === '30d' ? 'bg-white text-purple-700 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900'}`}
            >
              30 Dias
            </button>
          </div>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2.5 rounded-xl border border-violet-100 bg-white hover:bg-violet-50 text-slate-600 hover:text-purple-700 transition-all cursor-pointer shadow-sm disabled:opacity-50"
            title="Atualizar Dados Operacionais"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Cards Superiores (Métricas) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Pedidos Hoje */}
        <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-violet-100 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Pedidos Hoje</span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
              <ShoppingBag className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {metrics?.pedidosHoje !== undefined ? metrics.pedidosHoje : '—'}
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1 font-medium">
            <Clock className="w-3 h-3 text-slate-400" /> Atualizado em tempo real via API
          </p>
        </div>

        {/* Metric 2: Ticket Médio */}
        <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-violet-100 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Ticket Médio</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {metrics?.ticketMedio !== undefined
              ? `R$ ${metrics.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : '—'}
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1 font-medium">
            Média calculada por pedido fechado
          </p>
        </div>

        {/* Metric 3: Faturamento do Dia */}
        <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-violet-100 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Faturamento do Dia</span>
            <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {metrics?.faturamentoDia !== undefined
              ? `R$ ${metrics.faturamentoDia.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : '—'}
          </div>
          <p className="text-[11px] text-emerald-600 mt-1 flex items-center gap-0.5 font-bold">
            <ArrowUpRight className="w-3 h-3" /> Bruto consolidado
          </p>
        </div>

        {/* Metric 4: Taxa de Conversão */}
        <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-violet-100 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Taxa de Conversão</span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
              <UserCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {metrics?.taxaConversao !== undefined ? `${metrics.taxaConversao.toFixed(1)}%` : '—'}
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-medium">
            Atendimentos convertidos em venda
          </p>
        </div>
      </div>

      {/* Gráfico / Container de Eficiência da IA vs Atendimento Humano */}
      <div className="bg-white/90 backdrop-blur-md p-6 rounded-2xl border border-violet-100 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Bot className="w-5 h-5 text-purple-600" />
              Índice de Resolutividade da IA
            </h2>
            <p className="text-xs text-slate-500">
              Comparativo entre atendimentos finalizados 100% de forma autônoma pelo robô e transbordos manuais.
            </p>
          </div>

          {efficiency && (
            <span className="text-xs font-bold text-purple-700 bg-purple-50 border border-purple-200 px-3 py-1 rounded-full">
              {efficiency.porcentagemIa}% Automatizado
            </span>
          )}
        </div>

        {/* UI Container pronto para receber renderização de gráfico ou barras de proporção */}
        {efficiency ? (
          <div className="space-y-3 py-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span className="flex items-center gap-1.5 text-purple-700">
                <Bot className="w-4 h-4" /> IA Resolvidos: {efficiency.atendimentosIa}
              </span>
              <span className="flex items-center gap-1.5 text-slate-600">
                <UserCheck className="w-4 h-4" /> Transbordo Humano: {efficiency.atendimentosHumanos}
              </span>
            </div>

            <div className="w-full h-4 bg-slate-100 rounded-full overflow-hidden flex p-0.5 border border-slate-200/60">
              <div
                className="h-full bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(Math.max(efficiency.porcentagemIa, 0), 100)}%` }}
              />
              <div
                className="h-full bg-slate-300 rounded-full transition-all duration-500"
                style={{ width: `${100 - Math.min(Math.max(efficiency.porcentagemIa, 0), 100)}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 bg-slate-50 rounded-xl border border-dashed border-slate-200">
            <Bot className="w-8 h-8 text-slate-300 mb-2" />
            <p className="text-xs font-semibold text-slate-500">Aguardando dados de eficiência da API...</p>
            {/* Conectar via GET /api/v1/analytics/efficiency */}
          </div>
        )}
      </div>

      {/* Tabela de Últimos Pedidos */}
      <div className="bg-white/90 backdrop-blur-md rounded-2xl border border-violet-100 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-purple-600" />
              Últimos Pedidos em Fila
            </h2>
            <p className="text-xs text-slate-500">Acompanhamento dos pedidos recebidos via atendimento automático.</p>
          </div>
          <span className="text-xs font-bold text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
            {orders.length} {orders.length === 1 ? 'registro' : 'registros'}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/60 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-6">Identificador / Hora</th>
                <th className="py-3.5 px-6">Cliente</th>
                <th className="py-3.5 px-6">Valor Total</th>
                <th className="py-3.5 px-6">Tempo de Atendimento</th>
                <th className="py-3.5 px-6">Status do Pedido</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* Mapeamento dinâmico do array de pedidos enviado via props */}
              {orders.length > 0 ? (
                orders.map((pedido) => (
                  <tr key={pedido.id} className="hover:bg-violet-50/30 transition-colors">
                    <td className="py-4 px-6 font-bold text-slate-900">
                      #{pedido.id}
                      <span className="block text-xs font-medium text-slate-400">{pedido.horaPedido}</span>
                    </td>
                    <td className="py-4 px-6 font-semibold text-slate-800">
                      {pedido.clienteNome}
                    </td>
                    <td className="py-4 px-6 font-bold text-emerald-700">
                      R$ {pedido.valorTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-4 px-6 text-xs text-slate-500 font-medium">
                      {pedido.tempoAtendimento}
                    </td>
                    <td className="py-4 px-6">
                      {getStatusBadge(pedido.status)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-400">
                    <Inbox className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    <p className="text-xs font-semibold text-slate-500">Nenhum pedido mapeado na sessão atual.</p>
                    <p className="text-[11px] text-slate-400 mt-1">Conecte o endpoint GET /api/v1/orders ao estado do componente.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

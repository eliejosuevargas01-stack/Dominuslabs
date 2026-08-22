import { useState } from 'react';
import {
  Cpu,
  Bot,
  User,
  MessageSquare,
  Zap,
  AlertCircle,
  X,
  Calendar,
  Search
} from 'lucide-react';

export interface FranchiseQuota {
  usedTokens: number;
  totalTokens: number;
  usedMessages: number;
  totalMessages: number;
  renewsAt?: string;
  overageCostPerThousandTokens?: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ia' | 'system';
  content: string;
  timestamp: string;
  tokensUsed?: number;
}

export interface AuditLogItem {
  id: string;
  clienteNome: string;
  telefone: string;
  dataHorario: string;
  resumoIntencao: string;
  totalTokens: number;
  transbordoHumano: boolean;
  historicoConversa: ChatMessage[];
}

interface AiIntelligenceProps {
  quota?: FranchiseQuota;
  logs?: AuditLogItem[];
  loading?: boolean;
  onSelectLog?: (log: AuditLogItem) => void;
}

export default function AiIntelligenceView({
  quota,
  logs = [],
  onSelectLog
}: AiIntelligenceProps) {
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Percentage Calculations
  const tokenPercentage = quota ? Math.min(Math.round((quota.usedTokens / quota.totalTokens) * 100), 100) : 0;
  const messagePercentage = quota ? Math.min(Math.round((quota.usedMessages / quota.totalMessages) * 100), 100) : 0;

  const handleLogClick = (log: AuditLogItem) => {
    setSelectedLog(log);
    if (onSelectLog) onSelectLog(log);
  };

  const filteredLogs = logs.filter(
    (l) =>
      l.clienteNome.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.telefone.includes(searchTerm) ||
      l.resumoIntencao.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4   p-6 rounded-2xl border border-zinc-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-display font-extrabold text-zinc-900 flex items-center gap-2.5">
            <Cpu className="w-7 h-7 text-purple-600" />
            Transparência & Consumo da IA
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Monitoramento de franquia de tokens/mensagens e auditoria em tempo real das interações com clientes.
          </p>
        </div>
      </div>

      {/* Medidor de Franquia */}
      <div className="  p-6 rounded-2xl border border-zinc-200 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
          <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-500" />
            Consumo da Franquia de Processamento
          </h2>
          {quota?.renewsAt && (
            <span className="text-xs font-semibold text-zinc-500 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Renova em: {quota.renewsAt}
            </span>
          )}
        </div>

        {quota ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Tokens Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-zinc-700">Tokens Processados</span>
                <span className="text-purple-700">
                  {quota.usedTokens.toLocaleString('pt-BR')} / {quota.totalTokens.toLocaleString('pt-BR')} ({tokenPercentage}%)
                </span>
              </div>
              <div className="w-full h-3.5 bg-zinc-100 rounded-full overflow-hidden p-0.5 border border-zinc-200/60">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    tokenPercentage > 90 ? 'bg-rose-500' : tokenPercentage > 75 ? 'bg-amber-500' : 'bg-purple-600'
                  }`}
                  style={{ width: `${tokenPercentage}%` }}
                />
              </div>
            </div>

            {/* Messages Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-bold">
                <span className="text-zinc-700">Mensagens Enviadas</span>
                <span className="text-indigo-700">
                  {quota.usedMessages.toLocaleString('pt-BR')} / {quota.totalMessages.toLocaleString('pt-BR')} ({messagePercentage}%)
                </span>
              </div>
              <div className="w-full h-3.5 bg-zinc-100 rounded-full overflow-hidden p-0.5 border border-zinc-200/60">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    messagePercentage > 90 ? 'bg-rose-500' : messagePercentage > 75 ? 'bg-amber-500' : 'bg-indigo-600'
                  }`}
                  style={{ width: `${messagePercentage}%` }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="py-6 text-center text-xs font-semibold text-zinc-400 bg-zinc-50 rounded-xl border border-dashed border-zinc-200">
            Aguardando carregamento da franquia via GET /api/v1/ai/quota...
          </div>
        )}

        <div className="flex items-center gap-2 p-3 rounded-xl bg-amber-50/80 border border-amber-200/60 text-amber-900 text-xs font-medium">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span>
            Excedentes do ciclo faturados a R$ {quota?.overageCostPerThousandTokens || '0,05'} por 1.000 tokens adicionais diretamente no plano contratado.
          </span>
        </div>
      </div>

      {/* Audit Logs and Split Chat View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Logs List Column */}
        <div className={`${selectedLog ? 'lg:col-span-6' : 'lg:col-span-12'} transition-all`}>
          <div className="  rounded-2xl border border-zinc-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-zinc-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-purple-600" />
                Logs de Auditoria de Conversas
              </h2>

              <div className="relative">
                <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar por cliente ou intenção..."
                  className="pl-9 pr-3 py-1.5 text-xs rounded-xl border border-zinc-200 focus:border-purple-500 outline-none w-full sm:w-64"
                />
              </div>
            </div>

            <div className="divide-y divide-zinc-100 max-h-[550px] overflow-y-auto">
              {filteredLogs.length > 0 ? (
                filteredLogs.map((log) => {
                  const isSelected = selectedLog?.id === log.id;
                  return (
                    <div
                      key={log.id}
                      onClick={() => handleLogClick(log)}
                      className={`p-4 cursor-pointer transition-all hover:bg-purple-50/40 ${
                        isSelected ? 'bg-purple-50/80 border-l-4 border-purple-600' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-zinc-900 text-sm">{log.clienteNome}</span>
                        <span className="text-[11px] text-zinc-400">{log.dataHorario}</span>
                      </div>
                      <p className="text-xs text-zinc-600 line-clamp-1 mb-2">{log.resumoIntencao}</p>

                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-zinc-400 font-mono">{log.totalTokens} tokens</span>
                        {log.transbordoHumano ? (
                          <span className="px-2 py-0.5 font-semibold text-amber-800 bg-amber-100 rounded-md">
                            Transbordo Humano
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 font-semibold text-emerald-800 bg-emerald-100 rounded-md">
                            100% Autônomo
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-xs text-zinc-400">
                  Nenhum registro de auditoria carregado no momento.
                  {/* Conectar via GET /api/v1/ai/audit-logs */}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Chat History Panel (when log is selected) */}
        {selectedLog && (
          <div className="lg:col-span-6   rounded-2xl border border-zinc-200 shadow-sm flex flex-col h-[580px]">
            {/* Panel Header */}
            <div className="p-4 border-b border-zinc-100 flex items-center justify-between  rounded-t-2xl">
              <div>
                <h3 className="font-bold text-zinc-900 text-sm">{selectedLog.clienteNome}</h3>
                <p className="text-xs text-zinc-500">{selectedLog.telefone}</p>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 hover: cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 ">
              {selectedLog.historicoConversa.map((msg) => {
                const isIa = msg.sender === 'ia';
                return (
                  <div
                    key={msg.id}
                    className={`flex gap-2 max-w-[85%] ${isIa ? 'ml-auto flex-row-reverse' : ''}`}
                  >
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                        isIa ? 'bg-purple-600 text-white' : 'bg-zinc-200 text-zinc-700'
                      }`}
                    >
                      {isIa ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                    </div>
                    <div>
                      <div
                        className={`p-3 rounded-2xl text-xs leading-relaxed ${
                          isIa
                            ? 'bg-purple-600 text-white rounded-tr-none shadow-sm'
                            : 'bg-white text-zinc-800 border border-zinc-200 rounded-tl-none'
                        }`}
                      >
                        {msg.content}
                      </div>
                      <span className="text-[10px] text-zinc-400 px-1 mt-0.5 block">
                        {msg.timestamp} {msg.tokensUsed ? `• ${msg.tokensUsed} tokens` : ''}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

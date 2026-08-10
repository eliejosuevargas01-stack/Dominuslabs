import { useState, useEffect, useMemo, useRef } from 'react';
import { 
  MessageSquare, Search, Send, Loader2, Sparkles, Check, CheckCheck,
  RefreshCw, Filter, Phone, User, Radio, ArrowLeft
} from 'lucide-react';
import { API_BASE, fetchWithAuth, fetchWhatsappSessions, sendWhatsappMessage } from '../services/api';

// Paleta de Cores Únicas e Vibrantes para cada Instância de WhatsApp
export const WHATSAPP_COLOR_PALETTES = [
  { 
    name: 'emerald', 
    bg: 'bg-emerald-500', 
    text: 'text-emerald-700', 
    bgLight: 'bg-emerald-50', 
    border: 'border-emerald-200', 
    badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    hex: '#10B981', 
    glow: 'shadow-emerald-500/20' 
  },
  { 
    name: 'violet', 
    bg: 'bg-violet-600', 
    text: 'text-violet-700', 
    bgLight: 'bg-violet-50', 
    border: 'border-violet-200', 
    badgeBg: 'bg-violet-100 text-violet-800 border-violet-300',
    hex: '#8B5CF6', 
    glow: 'shadow-violet-500/20' 
  },
  { 
    name: 'amber', 
    bg: 'bg-amber-500', 
    text: 'text-amber-700', 
    bgLight: 'bg-amber-50', 
    border: 'border-amber-200', 
    badgeBg: 'bg-amber-100 text-amber-800 border-amber-300',
    hex: '#F59E0B', 
    glow: 'shadow-amber-500/20' 
  },
  { 
    name: 'cyan', 
    bg: 'bg-cyan-500', 
    text: 'text-cyan-700', 
    bgLight: 'bg-cyan-50', 
    border: 'border-cyan-200', 
    badgeBg: 'bg-cyan-100 text-cyan-800 border-cyan-300',
    hex: '#06B6D4', 
    glow: 'shadow-cyan-500/20' 
  },
  { 
    name: 'rose', 
    bg: 'bg-rose-500', 
    text: 'text-rose-700', 
    bgLight: 'bg-rose-50', 
    border: 'border-rose-200', 
    badgeBg: 'bg-rose-100 text-rose-800 border-rose-300',
    hex: '#F43F5E', 
    glow: 'shadow-rose-500/20' 
  },
  { 
    name: 'indigo', 
    bg: 'bg-indigo-600', 
    text: 'text-indigo-700', 
    bgLight: 'bg-indigo-50', 
    border: 'border-indigo-200', 
    badgeBg: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    hex: '#6366F1', 
    glow: 'shadow-indigo-500/20' 
  },
  { 
    name: 'teal', 
    bg: 'bg-teal-500', 
    text: 'text-teal-700', 
    bgLight: 'bg-teal-50', 
    border: 'border-teal-200', 
    badgeBg: 'bg-teal-100 text-teal-800 border-teal-300',
    hex: '#14B8A6', 
    glow: 'shadow-teal-500/20' 
  },
  { 
    name: 'orange', 
    bg: 'bg-orange-500', 
    text: 'text-orange-700', 
    bgLight: 'bg-orange-50', 
    border: 'border-orange-200', 
    badgeBg: 'bg-orange-100 text-orange-800 border-orange-300',
    hex: '#F97316', 
    glow: 'shadow-orange-500/20' 
  }
];

export function getSessionColor(sessionId: string | undefined | null) {
  if (!sessionId) return WHATSAPP_COLOR_PALETTES[0];
  let hash = 0;
  for (let i = 0; i < sessionId.length; i++) {
    hash = sessionId.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % WHATSAPP_COLOR_PALETTES.length;
  return WHATSAPP_COLOR_PALETTES[index];
}

export default function CrmView() {
  const [leads, setLeads] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active filters & search
  const [selectedSessionFilter, setSelectedSessionFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeLead, setActiveLead] = useState<any | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [replyText, setReplyText] = useState('');
  const [replySessionId, setReplySessionId] = useState<string>('');

  const chatContainerRef = useRef<HTMLDivElement>(null);

  // 1. Carrega sessões de WhatsApp para identificar quais números estão conectados
  const loadSessions = async () => {
    try {
      const data = await fetchWhatsappSessions();
      let rawList: any[] = [];
      if (Array.isArray(data)) rawList = data;
      else if (data && Array.isArray(data.sessions)) rawList = data.sessions;
      setSessions(rawList);
    } catch (err) {
      console.warn("Falha ao carregar sessões de WhatsApp:", err);
    }
  };

  // 2. Carrega lista de conversas/leads
  const loadLeads = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/leads`);
      if (!res.ok) throw new Error('Falha ao carregar lista de conversas');
      const data = await res.json();
      
      // Ordena por última interação desc
      const sorted = Array.isArray(data) ? [...data].sort((a, b) => {
        const aDate = a.last_interaction ? new Date(a.last_interaction).getTime() : 0;
        const bDate = b.last_interaction ? new Date(b.last_interaction).getTime() : 0;
        return bDate - aDate;
      }) : [];

      setLeads(sorted);
      if (!silent && sorted.length > 0 && !activeLead) {
        setActiveLead(sorted[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao conectar à API');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  // 3. Carrega histórico de mensagens do lead ativo
  const loadConversation = async (leadId: string, silent = false) => {
    if (!silent) setLoadingMessages(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/conversations/${leadId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error("Erro ao carregar mensagens:", err);
    } finally {
      if (!silent) setLoadingMessages(false);
    }
  };

  useEffect(() => {
    loadSessions();
    loadLeads();
  }, []);

  useEffect(() => {
    if (activeLead) {
      loadConversation(activeLead.id);
      // Se a conversa tiver um whatsapp_instance associado, ajusta o seletor de resposta
      if (activeLead.whatsapp_instance || activeLead.session_id) {
        setReplySessionId(activeLead.whatsapp_instance || activeLead.session_id);
      }
    }
  }, [activeLead]);

  // Rola o chat para o fim quando novas mensagens chegam
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Escuta atualizações em tempo real (SSE)
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimeout: any = null;

    const connectSSE = () => {
      const token = localStorage.getItem("admin_token");
      if (!token) return;

      const sseUrl = `${API_BASE}/webhooks/events/crm-chats?token=${encodeURIComponent(token)}`;
      eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'reload') {
            loadLeads(true);
            if (activeLead && String(activeLead.id) === String(data.lead_id)) {
              loadConversation(data.lead_id, true);
            }
          }
        } catch (e) {
          if (event.data === 'reload') {
            loadLeads(true);
            if (activeLead) loadConversation(activeLead.id, true);
          }
        }
      };

      eventSource.onerror = (err) => {
        if (eventSource) eventSource.close();
        reconnectTimeout = setTimeout(connectSSE, 5000);
      };
    };

    connectSSE();

    const handleTokenRefreshed = () => {
      if (eventSource) eventSource.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      connectSSE();
    };

    window.addEventListener("token_refreshed", handleTokenRefreshed);

    return () => {
      window.removeEventListener("token_refreshed", handleTokenRefreshed);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (eventSource) eventSource.close();
    };
  }, [activeLead]);

  // Envio de Mensagem
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!replyText.trim() || !activeLead || sending) return;

    setSending(true);
    try {
      const payload = {
        lead_id: String(activeLead.id),
        phone: activeLead.whatsapp || activeLead.phone || activeLead.id,
        message: replyText.trim(),
        session_id: replySessionId || activeLead.whatsapp_instance || activeLead.session_id || undefined,
      };

      await sendWhatsappMessage(payload);
      setReplyText('');
      await loadConversation(activeLead.id, true);
      await loadLeads(true);
    } catch (err: any) {
      alert(`Falha ao enviar mensagem: ${err.message || err}`);
    } finally {
      setSending(false);
    }
  };

  // Mapeia instâncias de WhatsApp disponíveis
  const connectedSessionsList = useMemo(() => {
    if (sessions.length > 0) return sessions;
    
    // Fallback: extrai sessões únicas a partir dos próprios leads cadastrados
    const found = new Set<string>();
    leads.forEach(l => {
      const sName = l.whatsapp_instance || l.session_id;
      if (sName) found.add(sName);
    });
    return Array.from(found).map(id => ({ name: id, status: 'CONNECTED' }));
  }, [sessions, leads]);

  // Filtra conversas na Bandeja de Entrada por Instância e Termo de Busca
  const filteredLeads = useMemo(() => {
    return leads.filter(lead => {
      const leadSession = lead.whatsapp_instance || lead.session_id || 'default';
      
      // Filtro por WhatsApp
      if (selectedSessionFilter !== 'ALL' && leadSession !== selectedSessionFilter) {
        return false;
      }

      // Filtro por Busca (Nome, Telefone ou Mensagem)
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const nameMatch = (lead.nome || '').toLowerCase().includes(query);
        const companyMatch = (lead.nome_empresa || '').toLowerCase().includes(query);
        const phoneMatch = (lead.whatsapp || lead.phone || '').includes(query);
        const msgMatch = (lead.ultima_mensagem || '').toLowerCase().includes(query);
        return nameMatch || companyMatch || phoneMatch || msgMatch;
      }

      return true;
    });
  }, [leads, selectedSessionFilter, searchTerm]);

  return (
    <div className="min-h-screen bg-slate-50/50 p-4 md:p-8 space-y-6">
      {/* Header Principal da Bandeja de Entrada */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-6 rounded-3xl border border-violet-100/50 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-gradient-to-br from-violet-600 to-indigo-600 text-white rounded-2xl shadow-md shadow-violet-500/20">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-display font-extrabold text-2xl text-slate-800 tracking-tight">
                Bandeja de Entrada Multi-WhatsApp
              </h1>
              <p className="text-sm font-medium text-slate-500">
                Central unificada para receber e responder conversas de todas as suas instâncias conectadas.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => { loadSessions(); loadLeads(); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-violet-50 text-slate-700 hover:text-purple-700 font-semibold text-xs rounded-xl border border-slate-200/60 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Atualizar Conversas
          </button>
        </div>
      </div>

      {/* Barra de Filtros por Instância de WhatsApp (Cada uma com Cor Única) */}
      <div className="bg-white/80 backdrop-blur-md p-4 rounded-2xl border border-violet-100/50 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
          <Filter className="w-3.5 h-3.5" />
          <span>Filtrar por WhatsApp Conectado</span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          {/* Opção Todos os WhatsApps */}
          <button
            onClick={() => setSelectedSessionFilter('ALL')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap border ${
              selectedSessionFilter === 'ALL'
                ? 'bg-slate-900 text-white border-slate-900 shadow-md shadow-slate-900/10'
                : 'bg-slate-50 text-slate-600 border-slate-200/60 hover:bg-slate-100'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Todos os WhatsApps</span>
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-white/20 text-[10px]">
              {leads.length}
            </span>
          </button>

          {/* Botões para cada WhatsApp Conectado com Cor Única */}
          {connectedSessionsList.map((session, index) => {
            const sName = session.name || session.session_name || `Instância ${index + 1}`;
            const palette = getSessionColor(sName);
            const isSelected = selectedSessionFilter === sName;
            const chatCount = leads.filter(l => (l.whatsapp_instance || l.session_id) === sName).length;

            return (
              <button
                key={sName}
                onClick={() => setSelectedSessionFilter(sName)}
                style={{
                  borderColor: isSelected ? palette.hex : undefined
                }}
                className={`flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap border ${
                  isSelected
                    ? `${palette.bg} text-white shadow-md ${palette.glow}`
                    : `${palette.bgLight} ${palette.text} ${palette.border} hover:opacity-90`
                }`}
              >
                {/* Dot com a Cor Única */}
                <span 
                  className={`w-2.5 h-2.5 rounded-full shadow-sm ${isSelected ? 'bg-white' : palette.bg}`}
                />
                <span>{sName}</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                  isSelected ? 'bg-white/20 text-white' : palette.badgeBg
                }`}>
                  {chatCount} {chatCount === 1 ? 'chat' : 'chats'}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Grid Principal: Lista de Conversas (Esquerda) + Chat Ativo (Direita) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LADO ESQUERDO: Lista da Bandeja de Entrada (4 colunas) */}
        <div className={`lg:col-span-5 bg-white/90 backdrop-blur-md rounded-3xl border border-violet-100/50 shadow-sm flex flex-col h-[750px] overflow-hidden ${
          activeLead ? 'hidden lg:flex' : 'flex'
        }`}>
          {/* Busca na Bandeja */}
          <div className="p-4 border-b border-slate-100 bg-slate-50/50">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar por nome, telefone ou mensagem..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white rounded-xl border border-slate-200/70 text-xs font-medium text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all"
              />
            </div>
          </div>

          {/* Feed de Conversas */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100/80">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-400 space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
                <p className="text-xs font-medium">Carregando bandeja de entrada...</p>
              </div>
            ) : filteredLeads.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-400 space-y-3 p-6 text-center">
                <MessageSquare className="w-10 h-10 text-slate-300" />
                <p className="text-sm font-semibold text-slate-600">Nenhuma conversa encontrada</p>
                <p className="text-xs text-slate-400 max-w-xs">
                  {searchTerm ? 'Tente alterar os termos de busca.' : 'As novas mensagens recebidas pelos WhatsApps conectados aparecerão aqui.'}
                </p>
              </div>
            ) : (
              filteredLeads.map((lead) => {
                const sessionName = lead.whatsapp_instance || lead.session_id || 'Indefinido';
                const palette = getSessionColor(sessionName);
                const isSelected = activeLead && String(activeLead.id) === String(lead.id);

                return (
                  <div
                    key={lead.id}
                    onClick={() => setActiveLead(lead)}
                    className={`p-4 transition-all cursor-pointer flex items-start gap-3 hover:bg-violet-50/40 relative ${
                      isSelected ? 'bg-violet-50/80 border-l-4 border-purple-600' : ''
                    }`}
                  >
                    {/* Avatar do Lead com a Cor da Instância do WhatsApp */}
                    <div 
                      className={`w-11 h-11 rounded-2xl flex items-center justify-center font-bold text-white shadow-sm flex-shrink-0 relative ${palette.bg}`}
                    >
                      {(lead.nome || lead.nome_empresa || 'W')[0].toUpperCase()}

                      {/* Pill Indicador de Cor no Avatar */}
                      <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-white flex items-center justify-center shadow-sm">
                        <span className={`w-2.5 h-2.5 rounded-full ${palette.bg}`} />
                      </span>
                    </div>

                    {/* Conteúdo da Conversa */}
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="font-bold text-xs text-slate-800 truncate">
                          {lead.nome || lead.nome_empresa || lead.whatsapp || lead.phone || 'Contato sem nome'}
                        </h3>
                        {lead.last_interaction && (
                          <span className="text-[10px] font-semibold text-slate-400 whitespace-nowrap">
                            {new Date(lead.last_interaction).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>

                      {/* Tag Única com a Cor do WhatsApp Que Recebeu a Mensagem */}
                      <div className="flex items-center gap-1.5">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-extrabold border ${palette.badgeBg}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${palette.bg}`} />
                          {sessionName}
                        </span>
                      </div>

                      {/* Prévia da Mensagem */}
                      <p className="text-xs text-slate-500 truncate font-normal">
                        {lead.ultima_mensagem || 'Sem histórico de texto...'}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* LADO DIREITO: Painel de Chat Ativo (7 colunas) */}
        <div className={`lg:col-span-7 bg-white/90 backdrop-blur-md rounded-3xl border border-violet-100/50 shadow-sm flex flex-col h-[750px] overflow-hidden ${
          !activeLead ? 'hidden lg:flex' : 'flex'
        }`}>
          {activeLead ? (
            <>
              {/* Header do Chat Ativo */}
              <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    onClick={() => setActiveLead(null)}
                    className="lg:hidden p-1.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-purple-700"
                  >
                    <ArrowLeft className="w-4 h-4" />
                  </button>

                  {/* Avatar do Lead */}
                  {(() => {
                    const sessionName = activeLead.whatsapp_instance || activeLead.session_id;
                    const palette = getSessionColor(sessionName);
                    return (
                      <div className={`w-10 h-10 rounded-2xl flex items-center justify-center font-bold text-white shadow-sm flex-shrink-0 ${palette.bg}`}>
                        {(activeLead.nome || activeLead.nome_empresa || 'W')[0].toUpperCase()}
                      </div>
                    );
                  })()}

                  <div className="min-w-0">
                    <h2 className="font-extrabold text-sm text-slate-800 truncate">
                      {activeLead.nome || activeLead.nome_empresa || 'Contato WhatsApp'}
                    </h2>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
                        <Phone className="w-3 h-3 text-slate-400" />
                        {activeLead.whatsapp || activeLead.phone || 'Sem número'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Badge da Instância do WhatsApp Conectada com a Cor Única */}
                {(() => {
                  const sessionName = activeLead.whatsapp_instance || activeLead.session_id || replySessionId || 'Desconhecido';
                  const palette = getSessionColor(sessionName);
                  return (
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-bold ${palette.badgeBg}`}>
                      <span className={`w-2 h-2 rounded-full animate-pulse ${palette.bg}`} />
                      <span>WhatsApp: {sessionName}</span>
                    </div>
                  );
                })()}
              </div>

              {/* Área de Mensagens do Chat */}
              <div 
                ref={chatContainerRef}
                className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 bg-gradient-to-b from-slate-50/30 to-white"
              >
                {loadingMessages ? (
                  <div className="flex items-center justify-center py-20 text-slate-400 space-y-2">
                    <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-400 text-center space-y-2">
                    <Sparkles className="w-8 h-8 text-violet-300 animate-pulse" />
                    <p className="text-xs font-medium">Inicie a conversa enviando uma mensagem abaixo.</p>
                  </div>
                ) : (
                  messages.map((msg, idx) => {
                    const isOutgoing = msg.direction === 'outgoing' || msg.sent_by_user === true;
                    return (
                      <div
                        key={idx}
                        className={`flex flex-col ${isOutgoing ? 'items-end' : 'items-start'}`}
                      >
                        <div
                          className={`max-w-[85%] md:max-w-[75%] px-4 py-3 rounded-2xl text-xs font-medium leading-relaxed shadow-sm ${
                            isOutgoing
                              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-br-none'
                              : 'bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200/50'
                          }`}
                        >
                          <p className="whitespace-pre-wrap break-words">{msg.content || msg.message}</p>
                          <div className={`flex items-center justify-end gap-1 mt-1 text-[9px] ${
                            isOutgoing ? 'text-purple-200' : 'text-slate-400'
                          }`}>
                            <span>
                              {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                            </span>
                            {isOutgoing && <CheckCheck className="w-3 h-3 text-purple-200" />}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Formulário de Resposta no WhatsApp */}
              <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-100 bg-white space-y-3">
                {/* Seletor de Sessão do WhatsApp com Cores Únicas */}
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Radio className="w-3 h-3" />
                    Disparar através do WhatsApp:
                  </span>
                  
                  <select
                    value={replySessionId}
                    onChange={(e) => setReplySessionId(e.target.value)}
                    className="px-3 py-1 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-purple-500/20 cursor-pointer"
                  >
                    {connectedSessionsList.map((s, idx) => {
                      const name = s.name || s.session_name || `WhatsApp ${idx + 1}`;
                      return (
                        <option key={name} value={name}>
                          ● {name} ({s.status || 'Ativo'})
                        </option>
                      );
                    })}
                  </select>
                </div>

                {/* Textarea + Botão Enviar */}
                <div className="flex items-end gap-2">
                  <textarea
                    rows={2}
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder="Digite sua resposta... (Pressione Enter para enviar)"
                    className="flex-1 p-3 bg-slate-50 border border-slate-200/80 rounded-2xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 focus:bg-white transition-all resize-none"
                  />

                  <button
                    type="submit"
                    disabled={sending || !replyText.trim()}
                    className={`p-3.5 rounded-2xl font-bold text-xs text-white flex items-center justify-center transition-all cursor-pointer shadow-md ${
                      sending || !replyText.trim()
                        ? 'bg-slate-300 cursor-not-allowed shadow-none'
                        : 'bg-gradient-to-r from-purple-600 via-indigo-600 to-emerald-600 hover:opacity-95 shadow-purple-600/20 active:scale-95'
                    }`}
                  >
                    {sending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400 space-y-3">
              <div className="p-4 bg-violet-50 text-violet-600 rounded-3xl">
                <MessageSquare className="w-10 h-10" />
              </div>
              <h3 className="font-bold text-slate-700 text-base">Nenhuma conversa selecionada</h3>
              <p className="text-xs text-slate-400 max-w-sm">
                Selecione um contato na bandeja de entrada ao lado para visualizar o histórico de mensagens e responder.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

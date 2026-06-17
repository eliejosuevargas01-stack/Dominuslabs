import { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Users, UserCheck, MessageSquare, Send, Check, 
  Clipboard, Search, Loader2, 
  Sparkles, MessageCircle, AlertCircle, FileText,
  ChevronLeft, ChevronRight
} from 'lucide-react';
import { API_BASE, fetchWithAuth } from '../services/api';

export default function CrmView() {
  const [leads, setLeads] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [loadingLeads, setLoadingLeads] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [statusFilter, setStatusFilter] = useState('');
  const [originFilter, setOriginFilter] = useState('');
  const [segmentFilter, setSegmentFilter] = useState('');
  const [falhaFilter, setFalhaFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [kpiFilter, setKpiFilter] = useState<string | null>(null);

  // Selected Lead Details drawer
  const [selectedLead, setSelectedLead] = useState<any>(null);
  const [editingLead, setEditingLead] = useState<any>(null);
  const [updatingLead, setUpdatingLead] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  // Conversation & Messaging State
  const [messages, setMessages] = useState<any[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [whatsappMessage, setWhatsappMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);



  // Proposal copy feedback
  const [copiedProposal, setCopiedProposal] = useState(false);

  const chatContainerRef = useRef<HTMLDivElement>(null);

  const statuses = [
    'Prospectado',
    'Abordagem Enviada',
    'Em Qualificação',
    'Diagnóstico/Proposta',
    'Negociando/Objeção',
    'Fechado (Win)',
    'Perdido (Loss)'
  ];


  // Dynamic filter lists extracted from loaded leads
  const dynamicStatuses = useMemo(() => {
    const s = new Set<string>();
    leads.forEach(l => {
      if (l.status) s.add(l.status);
    });
    return Array.from(s).sort();
  }, [leads]);

  const dynamicOrigins = useMemo(() => {
    const s = new Set<string>();
    leads.forEach(l => {
      if (l.origin) s.add(l.origin);
    });
    return Array.from(s).sort();
  }, [leads]);

  const dynamicSegments = useMemo(() => {
    const s = new Set<string>();
    leads.forEach(l => {
      if (l.segmento && l.segmento.trim() !== '') s.add(l.segmento);
    });
    return Array.from(s).sort();
  }, [leads]);

  const dynamicFalhas = useMemo(() => {
    const s = new Set<string>();
    leads.forEach(l => {
      if (l.falha_identificada && l.falha_identificada.trim() !== '') s.add(l.falha_identificada);
    });
    return Array.from(s).sort();
  }, [leads]);

  // Fetch initial leads and dashboard metrics
  const fetchData = async () => {
    setLoadingLeads(true);
    setLoadingMetrics(true);
    setError(null);

    try {
      // 1. Fetch leads
      const leadsRes = await fetchWithAuth(`${API_BASE}/crm/leads`);
      if (!leadsRes.ok) throw new Error('Falha ao buscar leads');
      const leadsData = await leadsRes.json();
      
      // 3. Auto-advance leads with chat history from Prospectado → Abordagem Enviada
      const leadsToAdvance = leadsData.filter(
        (l: any) => l.mensagem_enviada === true && l.status === 'Prospectado'
      );

      if (leadsToAdvance.length > 0) {
        // Fire all PUT requests in parallel
        await Promise.allSettled(
          leadsToAdvance.map((l: any) =>
            fetchWithAuth(`${API_BASE}/crm/leads/${l.id}`, {
              method: 'PUT',
              body: JSON.stringify({ ...l, status: 'Abordagem Enviada' })
            })
          )
        );

        // Reflect changes locally
        leadsData.forEach((l: any) => {
          if (l.mensagem_enviada === true && l.status === 'Prospectado') {
            l.status = 'Abordagem Enviada';
          }
        });
      }

      // Sort leads: those with sent messages first, then by last_interaction descending
      const sortedLeads = [...leadsData].sort((a: any, b: any) => {
        const aSent = a.mensagem_enviada ? 1 : 0;
        const bSent = b.mensagem_enviada ? 1 : 0;
        if (aSent !== bSent) {
          return bSent - aSent; // mensagem_enviada first
        }
        const aDate = a.last_interaction ? new Date(a.last_interaction).getTime() : 0;
        const bDate = b.last_interaction ? new Date(b.last_interaction).getTime() : 0;
        return bDate - aDate;
      });
      
      setLeads(sortedLeads);
      setLoadingLeads(false);

      // 2. Fetch metrics
      const metricsRes = await fetchWithAuth(`${API_BASE}/crm/dashboard`);
      if (!metricsRes.ok) throw new Error('Falha ao buscar indicadores');
      const metricsData = await metricsRes.json();
      setMetrics(metricsData);
      setLoadingMetrics(false);
    } catch (err: any) {
      setError(err.message || 'Erro de conexão com a API.');
      setLoadingLeads(false);
      setLoadingMetrics(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Scroll to bottom of chat container locally
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Fetch conversation and activities for selected lead
  const handleSelectLead = async (lead: any) => {
    setSelectedLead(lead);
    setEditingLead({ ...lead });
    setUpdateSuccess(false);
    setMessages([]);
    
    setLoadingMessages(true);

    try {
      // Fetch messages
      const msgRes = await fetchWithAuth(`${API_BASE}/crm/conversations/${lead.id}`);
      if (msgRes.ok) {
        const msgData = await msgRes.json();
        setMessages(msgData);
      }
      setLoadingMessages(false);
    } catch (err) {
      setLoadingMessages(false);
    }
  };

  // Dynamically compute and save the contact method based on priority
  const handleFieldChange = (field: string, value: string) => {
    if (!editingLead) return;
    const updated = { ...editingLead, [field]: value };
    
    // Recalculate origin (Contact Method)
    const wa = field === 'whatsapp' ? value : (updated.whatsapp || '');
    const ig = field === 'instagram' ? value : (updated.instagram || '');
    const em = field === 'email' ? value : (updated.email || '');
    
    if (wa && wa.trim() !== '' && wa.trim().toLowerCase() !== 'null') {
      updated.origin = 'WhatsApp';
    } else if (ig && ig.trim() !== '' && ig.trim().toLowerCase() !== 'null') {
      updated.origin = 'Instagram';
    } else if (em && em.trim() !== '' && em.trim().toLowerCase() !== 'null') {
      updated.origin = 'E-mail';
    } else {
      updated.origin = 'Outro';
    }
    
    setEditingLead(updated);
  };

  // Save Lead profile updates
  const handleSaveLeadDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLead) return;
    setUpdatingLead(true);
    setUpdateSuccess(false);

    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/leads/${editingLead.id}`, {
        method: 'PUT',
        body: JSON.stringify(editingLead)
      });
      if (!res.ok) throw new Error('Erro ao salvar dados do lead');
      const updatedLead = await res.json();
      
      // Update local state
      setLeads(leads.map(l => l.id === updatedLead.id ? updatedLead : l));
      setSelectedLead(updatedLead);
      setUpdateSuccess(true);
      
      // Refresh dashboard metrics in case status changed
      const metricsRes = await fetchWithAuth(`${API_BASE}/crm/dashboard`);
      if (metricsRes.ok) {
        setMetrics(await metricsRes.json());
      }
    } catch (err: any) {
      alert(err.message || 'Erro ao salvar lead.');
    } finally {
      setUpdatingLead(false);
    }
  };



  // Send WhatsApp message
  const handleSendWhatsapp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whatsappMessage.trim() || !selectedLead) return;
    setSendingMessage(true);

    const payload = {
      lead_id: selectedLead.id,
      phone: selectedLead.whatsapp || '',
      message: whatsappMessage
    };

    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/messages/send`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Falha ao enviar mensagem');
      const newMsg = await res.json();
      
      // Update messages panel immediately
      setMessages([...messages, newMsg]);
      setWhatsappMessage('');

      // Update lead last interaction time, set message_sent, and auto-advance status
      setLeads(leads.map(l => {
        if (l.id !== selectedLead.id) return l;
        const updated = { ...l, last_interaction: new Date().toISOString(), mensagem_enviada: true };
        // Auto-advance from Prospectado to Abordagem Enviada on first contact
        if (l.status === 'Prospectado') {
          updated.status = 'Abordagem Enviada';
        }
        return updated;
      }));

      // Auto-advance status on backend if it was Prospectado
      if (selectedLead.status === 'Prospectado') {
        await fetchWithAuth(`${API_BASE}/crm/leads/${selectedLead.id}`, {
          method: 'PUT',
          body: JSON.stringify({ ...selectedLead, status: 'Abordagem Enviada' })
        });
        setSelectedLead({ ...selectedLead, status: 'Abordagem Enviada' });
        if (editingLead && editingLead.id === selectedLead.id) {
          setEditingLead({ ...editingLead, status: 'Abordagem Enviada' });
        }
      }



      // Refresh dashboard metrics
      const metricsRes = await fetchWithAuth(`${API_BASE}/crm/dashboard`);
      if (metricsRes.ok) {
        setMetrics(await metricsRes.json());
      }
    } catch (err: any) {
      alert(err.message || 'Erro ao enviar mensagem.');
    } finally {
      setSendingMessage(false);
    }
  };

  // Copy proposal text to clipboard & open Instagram & Log activity
  const handleSendProposal = async () => {
    if (!selectedLead || !selectedLead.proposal) return;
    
    // 1. Copy to clipboard
    navigator.clipboard.writeText(selectedLead.proposal);
    setCopiedProposal(true);
    setTimeout(() => setCopiedProposal(false), 2000);



    // 3. Open Instagram Direct Message if available
    if (selectedLead.instagram) {
      let username = selectedLead.instagram.trim();
      
      if (username.startsWith('@')) {
        username = username.substring(1);
      }
      
      if (username.includes('instagram.com') || username.includes('ig.me')) {
        try {
          let path = username;
          if (path.includes('://')) {
            path = path.split('://')[1];
          }
          if (path.startsWith('www.')) {
            path = path.substring(4);
          }
          if (path.startsWith('instagram.com/')) {
            path = path.replace('instagram.com/', '');
          } else if (path.startsWith('ig.me/')) {
            path = path.replace('ig.me/', '');
          }
          
          const parts = path.split('/');
          let candidate = parts[0];
          if (candidate.includes('?')) {
            candidate = candidate.split('?')[0];
          }
          if (candidate) {
            username = candidate;
          }
        } catch (e) {
          // Fallback
        }
      }
      
      const dmLink = `https://ig.me/m/${username}`;
      window.open(dmLink, '_blank');
    } else {
      alert('Texto da proposta copiado! Este lead não possui Instagram cadastrado.');
    }

    // 4. Auto-advance from Prospectado to Abordagem Enviada on first contact
    if (selectedLead.status === 'Prospectado') {
      setLeads(leads.map(l => l.id === selectedLead.id ? { ...l, status: 'Abordagem Enviada', mensagem_enviada: true } : l));
      setSelectedLead({ ...selectedLead, status: 'Abordagem Enviada' });
      if (editingLead && editingLead.id === selectedLead.id) {
        setEditingLead({ ...editingLead, status: 'Abordagem Enviada' });
      }
      await fetchWithAuth(`${API_BASE}/crm/leads/${selectedLead.id}`, {
        method: 'PUT',
        body: JSON.stringify({ ...selectedLead, status: 'Abordagem Enviada' })
      });
    }
  };

  // Filter and sort leads locally
  const filteredLeads = useMemo(() => {
    const filtered = leads.filter(lead => {
      const matchesStatus = statusFilter ? lead.status === statusFilter : true;
      const matchesOrigin = originFilter ? lead.origin === originFilter : true;
      const matchesSegment = segmentFilter ? lead.segmento === segmentFilter : true;
      const matchesFalha = falhaFilter ? lead.falha_identificada === falhaFilter : true;
      
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = searchTerm 
        ? (String(lead.id || '').toLowerCase().includes(searchLower) ||
           lead.company_name?.toLowerCase().includes(searchLower) || 
           lead.email?.toLowerCase().includes(searchLower) ||
           String(lead.whatsapp || '').includes(searchTerm) ||
           lead.instagram?.toLowerCase().includes(searchLower) ||
           lead.responsible?.toLowerCase().includes(searchLower) ||
           lead.segmento?.toLowerCase().includes(searchLower) ||
           lead.falha_identificada?.toLowerCase().includes(searchLower) ||
           lead.solucao_recomendada?.toLowerCase().includes(searchLower) ||
           lead.notes?.toLowerCase().includes(searchLower) ||
           lead.proposal?.toLowerCase().includes(searchLower))
        : true;

      // Card-specific KPI filters
      let matchesKpi = true;
      if (kpiFilter === 'conversas') {
        matchesKpi = lead.mensagem_enviada === true || lead.status === 'Abordagem Enviada';
      } else if (kpiFilter === 'negociacoes') {
        matchesKpi = lead.status === 'Negociando/Objeção';
      } else if (kpiFilter === 'fechados') {
        matchesKpi = lead.status === 'Fechado (Win)';
      } else if (kpiFilter === 'pendentes') {
        matchesKpi = lead.status === 'RESPONDED' || (lead.has_messages === true && lead.mensagem_enviada === false);
      }
        
      return matchesStatus && matchesOrigin && matchesSegment && matchesFalha && matchesSearch && matchesKpi;
    });

    // Sort: leads with user messages sent first, then by last_interaction descending
    return filtered.sort((a, b) => {
      const aSent = a.mensagem_enviada ? 1 : 0;
      const bSent = b.mensagem_enviada ? 1 : 0;
      if (aSent !== bSent) {
        return bSent - aSent; // mensagem_enviada first
      }
      const aDate = a.last_interaction ? new Date(a.last_interaction).getTime() : 0;
      const bDate = b.last_interaction ? new Date(b.last_interaction).getTime() : 0;
      return bDate - aDate;
    });
  }, [leads, statusFilter, originFilter, segmentFilter, falhaFilter, searchTerm, kpiFilter]);

  // Pagination state and computation
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  const totalPages = Math.ceil(filteredLeads.length / itemsPerPage);

  const paginatedLeads = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredLeads.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredLeads, currentPage]);

  // Reset pagination to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, originFilter, segmentFilter, falhaFilter, searchTerm, kpiFilter]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Prospectado': return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'Abordagem Enviada': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Em Qualificação': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'Diagnóstico/Proposta': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'Negociando/Objeção': return 'bg-indigo-100 text-indigo-800 border-indigo-200';
      case 'Fechado (Win)': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'Perdido (Loss)': return 'bg-rose-100 text-rose-800 border-rose-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '-';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Title & Dashboard metrics */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-violet-600 animate-pulse" />
            CRM Comercial
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Centralize e gerencie sua esteira de vendas, leads prospectados, propostas e histórico de conversas.
          </p>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-xs font-semibold">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {loadingMetrics ? (
          Array(5).fill(0).map((_, i) => (
            <div key={i} className="glass-card p-6 h-24 flex items-center justify-center animate-pulse">
              <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
            </div>
          ))
        ) : metrics ? (
          <>
            <div 
              onClick={() => setKpiFilter(null)}
              className={`glass-card p-5 bg-white/70 border flex items-center gap-4 cursor-pointer transition-all hover:scale-[1.02] ${
                !kpiFilter ? 'border-purple-500 shadow-sm shadow-purple-100/50' : 'border-violet-100/30'
              }`}
            >
              <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center text-purple-700">
                <Users className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Leads</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.total_leads}</p>
              </div>
            </div>

            <div 
              onClick={() => setKpiFilter('conversas')}
              className={`glass-card p-5 bg-white/70 border flex items-center gap-4 cursor-pointer transition-all hover:scale-[1.02] ${
                kpiFilter === 'conversas' ? 'border-indigo-500 shadow-sm shadow-indigo-100/50' : 'border-violet-100/30'
              }`}
            >
              <div className="w-12 h-12 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-700">
                <MessageCircle className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Conversas Iniciadas</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.conversas_iniciadas}</p>
              </div>
            </div>

            <div 
              onClick={() => setKpiFilter('negociacoes')}
              className={`glass-card p-5 bg-white/70 border flex items-center gap-4 cursor-pointer transition-all hover:scale-[1.02] ${
                kpiFilter === 'negociacoes' ? 'border-blue-500 shadow-sm shadow-blue-100/50' : 'border-violet-100/30'
              }`}
            >
              <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-blue-700">
                <UserCheck className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Negociações</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.negociacoes}</p>
              </div>
            </div>

            <div 
              onClick={() => setKpiFilter('fechados')}
              className={`glass-card p-5 bg-white/70 border flex items-center gap-4 cursor-pointer transition-all hover:scale-[1.02] ${
                kpiFilter === 'fechados' ? 'border-emerald-500 shadow-sm shadow-emerald-100/50' : 'border-violet-100/30'
              }`}
            >
              <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700">
                <Check className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Clientes Fechados</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.clientes_fechados}</p>
              </div>
            </div>

            <div 
              onClick={() => setKpiFilter('pendentes')}
              className={`glass-card p-5 bg-white/70 border flex items-center gap-4 cursor-pointer transition-all hover:scale-[1.02] ${
                kpiFilter === 'pendentes' ? 'border-amber-500 shadow-sm shadow-amber-100/50' : 'border-violet-100/30'
              }`}
            >
              <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700">
                <MessageSquare className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Respostas Pendentes</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.respostas_pendentes}</p>
              </div>
            </div>
          </>
        ) : null}
      </div>

      {/* Main CRM Grid (Split Lead Table and Detail Drawer) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Leads Table Card */}
        <div className="xl:col-span-7 glass-card p-6 bg-white/70 border border-violet-100/30">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <h2 className="text-lg font-bold text-slate-800">Funil de Leads</h2>
            
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Text Search */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Buscar lead..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 pr-4 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs outline-none focus:border-purple-400 transition-all font-semibold"
                />
              </div>

              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs font-semibold outline-none focus:border-purple-400 cursor-pointer"
              >
                <option value="">Status (Todos)</option>
                {dynamicStatuses.map(st => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>

              {/* Origin Filter */}
              <select
                value={originFilter}
                onChange={(e) => setOriginFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs font-semibold outline-none focus:border-purple-400 cursor-pointer"
              >
                <option value="">Método de Contato (Todos)</option>
                {dynamicOrigins.map(or => (
                  <option key={or} value={or}>{or}</option>
                ))}
              </select>

              {/* Segment Filter */}
              <select
                value={segmentFilter}
                onChange={(e) => setSegmentFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs font-semibold outline-none focus:border-purple-400 cursor-pointer"
              >
                <option value="">Segmento (Todos)</option>
                {dynamicSegments.map(seg => (
                  <option key={seg} value={seg}>{seg}</option>
                ))}
              </select>

              {/* Failure Filter */}
              <select
                value={falhaFilter}
                onChange={(e) => setFalhaFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs font-semibold outline-none focus:border-purple-400 cursor-pointer"
              >
                <option value="">Falha Encontrada (Todos)</option>
                {dynamicFalhas.map(fal => (
                  <option key={fal} value={fal}>{fal}</option>
                ))}
              </select>

              {/* Clear Filters Button */}
              {(statusFilter || originFilter || segmentFilter || falhaFilter || searchTerm || kpiFilter) && (
                <button
                  onClick={() => {
                    setStatusFilter('');
                    setOriginFilter('');
                    setSegmentFilter('');
                    setFalhaFilter('');
                    setSearchTerm('');
                    setKpiFilter(null);
                  }}
                  className="px-3 py-2 rounded-xl border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold transition-all cursor-pointer shadow-sm shadow-rose-100/50"
                >
                  Limpar Filtros
                </button>
              )}
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto">
            {loadingLeads ? (
              <div className="py-20 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
              </div>
            ) : filteredLeads.length === 0 ? (
              <div className="py-20 text-center text-slate-400 text-sm font-semibold">
                Nenhum lead encontrado com os filtros selecionados.
              </div>
            ) : (
              <>
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-violet-100/50 text-xs font-bold text-slate-400 uppercase tracking-wider">
                      <th className="py-3 px-2 max-w-[80px]">ID</th>
                      <th className="py-3 px-2">Empresa</th>
                      <th className="py-3 px-2">Segmento</th>
                      <th className="py-3 px-2">Falha Encontrada</th>
                      <th className="py-3 px-2">WhatsApp</th>
                      <th className="py-3 px-2">Status</th>
                      <th className="py-3 px-2">Método de Contato</th>
                      <th className="py-3 px-2">Última Interação</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-violet-100/30 text-xs font-medium text-slate-600">
                    {paginatedLeads.map((lead) => {
                      const isSelected = selectedLead?.id === lead.id;
                      return (
                        <tr 
                          key={lead.id} 
                          onClick={() => handleSelectLead(lead)}
                          className={`hover:bg-violet-50/30 cursor-pointer transition-colors ${
                            isSelected ? 'bg-purple-50/50 font-semibold' : ''
                          }`}
                        >
                          <td className="py-3.5 px-2 text-slate-400 max-w-[80px] truncate" title={lead.id}>#{lead.id}</td>
                          <td className="py-3.5 px-2 text-slate-800">{lead.company_name}</td>
                          <td className="py-3.5 px-2 text-slate-500">{lead.segmento || '-'}</td>
                          <td className="py-3.5 px-2 text-slate-500">{lead.falha_identificada || '-'}</td>
                          <td className="py-3.5 px-2">{lead.whatsapp || '-'}</td>
                          <td className="py-3.5 px-2">
                            <span className={`px-2 py-0.5 rounded-full border text-[10px] uppercase font-bold tracking-wide ${getStatusColor(lead.status)}`}>
                              {lead.status}
                            </span>
                          </td>
                          <td className="py-3.5 px-2 text-slate-500">{lead.origin}</td>
                          <td className="py-3.5 px-2 text-slate-400">{formatDate(lead.last_interaction)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {/* Pagination Controls */}
                {filteredLeads.length > itemsPerPage && (
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6 pt-4 border-t border-violet-100/30 text-xs font-semibold text-slate-500">
                    <div>
                      Exibindo <span className="font-bold text-slate-700">{Math.min((currentPage - 1) * itemsPerPage + 1, filteredLeads.length)}</span> a{' '}
                      <span className="font-bold text-slate-700">{Math.min(currentPage * itemsPerPage, filteredLeads.length)}</span> de{' '}
                      <span className="font-bold text-slate-700">{filteredLeads.length}</span> leads
                    </div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <button
                        type="button"
                        onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                        disabled={currentPage === 1}
                        className="p-2 rounded-xl border border-violet-100 bg-white/50 hover:bg-violet-50 text-slate-600 disabled:opacity-40 disabled:hover:bg-white/50 transition-all cursor-pointer flex items-center justify-center animate-transition"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => {
                        const isCurrent = page === currentPage;
                        const isNear = Math.abs(page - currentPage) <= 1;
                        const isFirstOrLast = page === 1 || page === totalPages;
                        
                        if (!isNear && !isFirstOrLast) {
                          if (page === 2 && currentPage > 3) {
                            return <span key="ellipsis-start" className="px-1 text-slate-400 select-none">...</span>;
                          }
                          if (page === totalPages - 1 && currentPage < totalPages - 2) {
                            return <span key="ellipsis-end" className="px-1 text-slate-400 select-none">...</span>;
                          }
                          return null;
                        }
                        
                        return (
                          <button
                            key={page}
                            type="button"
                            onClick={() => setCurrentPage(page)}
                            className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                              isCurrent
                                ? 'border-purple-600 bg-purple-600 text-white shadow-md shadow-purple-200'
                                : 'border-violet-100 bg-white/50 hover:bg-violet-50 text-slate-600'
                            }`}
                          >
                            {page}
                          </button>
                        );
                      })}

                      <button
                        type="button"
                        onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                        disabled={currentPage === totalPages}
                        className="p-2 rounded-xl border border-violet-100 bg-white/50 hover:bg-violet-50 text-slate-600 disabled:opacity-40 disabled:hover:bg-white/50 transition-all cursor-pointer flex items-center justify-center animate-transition"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Lead Details & Messaging Drawer */}
        <div className="xl:col-span-5 glass-card bg-white/70 border border-violet-100/30 overflow-hidden">
          {selectedLead && editingLead ? (
            <div className="divide-y divide-violet-100/30">
              {/* Lead detail profile edit header */}
              <div className="p-6">
                <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-600 animate-pulse"></span>
                  Ficha do Lead: {selectedLead.company_name}
                </h3>
                
                {/* Proposal copy action */}
                {selectedLead.proposal && (
                  <button
                    onClick={handleSendProposal}
                    className="w-full flex items-center justify-center gap-2 mt-4 py-2.5 rounded-xl border border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-bold transition-all cursor-pointer shadow-sm shadow-purple-200/50"
                  >
                    {copiedProposal ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Texto Copiado! Abrindo aba...</span>
                      </>
                    ) : (
                      <>
                        <Clipboard className="w-3.5 h-3.5" />
                        <span>Enviar Proposta Comercial</span>
                      </>
                    )}
                  </button>
                )}

                {/* Edit Form */}
                <form onSubmit={handleSaveLeadDetails} className="space-y-3 mt-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Nome Empresa</label>
                      <input
                        type="text"
                        value={editingLead.company_name || ''}
                        onChange={(e) => setEditingLead({ ...editingLead, company_name: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">WhatsApp</label>
                      <input
                        type="text"
                        value={editingLead.whatsapp || ''}
                        onChange={(e) => handleFieldChange('whatsapp', e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Email</label>
                      <input
                        type="text"
                        value={editingLead.email || ''}
                        onChange={(e) => handleFieldChange('email', e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Nicho (Segmento)</label>
                      <input
                        type="text"
                        value={editingLead.segmento || ''}
                        onChange={(e) => setEditingLead({ ...editingLead, segmento: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</label>
                      <select
                        value={editingLead.status || 'Prospectado'}
                        onChange={(e) => setEditingLead({ ...editingLead, status: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                      >
                        {statuses.map(st => (
                          <option key={st} value={st}>{st}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Divisor & Metadados do Lead */}
                  <div className="pt-3 border-t border-slate-100/50 space-y-3">
                    <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Metadados do Lead</h5>
                    
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Origem</label>
                        <input
                          type="text"
                          disabled
                          value={editingLead.origem || 'meta_ads_library'}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-slate-100 text-xs font-semibold outline-none cursor-not-allowed opacity-75"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Localização</label>
                        <input
                          type="text"
                          value={editingLead.localizacao || ''}
                          onChange={(e) => setEditingLead({ ...editingLead, localizacao: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">LID</label>
                        <input
                          type="text"
                          value={editingLead.lid || ''}
                          onChange={(e) => setEditingLead({ ...editingLead, lid: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Score</label>
                        <input
                          type="text"
                          value={editingLead.score || ''}
                          onChange={(e) => setEditingLead({ ...editingLead, score: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Temperatura</label>
                        <input
                          type="text"
                          value={editingLead.temperatura || ''}
                          onChange={(e) => setEditingLead({ ...editingLead, temperatura: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Proposta Inicial</label>
                      <textarea
                        rows={2}
                        value={editingLead.proposta_inicial || ''}
                        onChange={(e) => setEditingLead({ ...editingLead, proposta_inicial: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-medium focus:border-purple-500 outline-none"
                      />
                    </div>
                  </div>

                  {/* Divisor & Site & Presença Digital */}
                  <div className="pt-3 border-t border-slate-100/50 space-y-3">
                    <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Presença Digital & Site</h5>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">URL Site</label>
                        <input
                          type="text"
                          value={editingLead.url_site || ''}
                          onChange={(e) => setEditingLead({ ...editingLead, url_site: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tem Site Próprio</label>
                        <select
                          value={editingLead.tem_site_proprio !== undefined && editingLead.tem_site_proprio !== null ? String(editingLead.tem_site_proprio) : 'false'}
                          onChange={(e) => setEditingLead({ ...editingLead, tem_site_proprio: e.target.value === 'true' })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                        >
                          <option value="true">Sim</option>
                          <option value="false">Não</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tem CTA</label>
                        <select
                          value={editingLead.tem_cta || 'não'}
                          onChange={(e) => setEditingLead({ ...editingLead, tem_cta: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                        >
                          <option value="sim">Sim</option>
                          <option value="não">Não</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tem Formulário Captação?</label>
                        <select
                          value={editingLead.tem_formulario || 'não'}
                          onChange={(e) => setEditingLead({ ...editingLead, tem_formulario: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                        >
                          <option value="sim">Sim</option>
                          <option value="não">Não</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">ID Anúncio Meta</label>
                        <input
                          type="text"
                          value={editingLead.id_anuncio_meta || ''}
                          onChange={(e) => setEditingLead({ ...editingLead, id_anuncio_meta: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Erros Identificados no Site</label>
                        <input
                          type="text"
                          value={editingLead.erros_identificados_site || ''}
                          onChange={(e) => setEditingLead({ ...editingLead, erros_identificados_site: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  {updateSuccess && (
                    <p className="text-[11px] font-semibold text-emerald-600 flex items-center gap-1">
                      <Check className="w-3.5 h-3.5" /> Salvo com sucesso!
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={updatingLead}
                    className="w-full py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-50 cursor-pointer"
                  >
                    {updatingLead ? 'Salvando...' : 'Salvar Alterações'}
                  </button>
                </form>
              </div>

              {/* Chat / Messages Panel */}
              <div className="p-6">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <MessageCircle className="w-4 h-4 text-emerald-500" />
                  Chat Integrado (WhatsApp/Instagram)
                </h4>

                {/* Messages Box */}
                <div ref={chatContainerRef} className="h-80 overflow-y-auto border border-violet-100/50 rounded-xl p-3 bg-slate-50/50 flex flex-col gap-2.5">
                  {loadingMessages ? (
                    <div className="flex-1 flex items-center justify-center">
                      <Loader2 className="w-5 h-5 text-purple-600 animate-spin" />
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center text-[11px] text-slate-400 font-semibold">
                      Nenhuma conversa iniciada.
                    </div>
                  ) : (
                    messages.map((msg: any, i) => {
                      const isUser = msg.sender === 'user';
                      return (
                        <div 
                          key={msg.id || i} 
                          className={`max-w-[85%] rounded-2xl p-2.5 text-xs ${
                            isUser 
                              ? 'bg-purple-600 text-white self-end rounded-tr-none' 
                              : 'bg-white text-slate-800 border border-slate-100 self-start rounded-tl-none shadow-sm'
                          }`}
                        >
                          <p className="font-medium leading-relaxed break-words">{msg.message}</p>
                          <div className={`text-[9px] mt-1 flex items-center gap-1 justify-end ${isUser ? 'text-purple-200' : 'text-slate-400'}`}>
                            <span>{msg.channel === 'whatsapp' ? 'WhatsApp' : 'Instagram'}</span>
                            <span>•</span>
                            <span>{formatDate(msg.timestamp)}</span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Chat Composer */}
                <form onSubmit={handleSendWhatsapp} className="flex gap-2 mt-3 items-end">
                  <textarea
                    placeholder="Digite uma mensagem via WhatsApp... (Pressione Enter para enviar, Shift+Enter para nova linha)"
                    value={whatsappMessage}
                    onChange={(e) => setWhatsappMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (whatsappMessage.trim() && !sendingMessage) {
                          handleSendWhatsapp(e);
                        }
                      }
                    }}
                    rows={3}
                    disabled={sendingMessage}
                    className="flex-grow px-3.5 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none resize-none min-h-[60px]"
                  />
                  <button
                    type="submit"
                    disabled={sendingMessage || !whatsappMessage.trim()}
                    className="p-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center shadow-md shadow-emerald-600/10 self-end h-10 w-10 flex-shrink-0"
                  >
                    {sendingMessage ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                  </button>
                </form>
              </div>


            </div>
          ) : (
            <div className="py-32 px-6 text-center text-slate-400 space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 shadow-inner">
                <FileText className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold">Nenhum Lead Selecionado</p>
              <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto">
                Selecione um lead na tabela ao lado para ver sua ficha detalhada, enviar propostas e conversar via WhatsApp.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

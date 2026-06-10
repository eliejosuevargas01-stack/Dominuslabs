import { useState, useEffect, useRef } from 'react';
import { 
  Users, UserCheck, MessageSquare, Send, Check, 
  Clipboard, Search, Loader2, 
  Activity, Sparkles, MessageCircle, AlertCircle, FileText
} from 'lucide-react';
import { API_BASE } from '../services/api';

export default function CrmView() {
  const [leads, setLeads] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [loadingLeads, setLoadingLeads] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [statusFilter, setStatusFilter] = useState('');
  const [originFilter, setOriginFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

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

  // Activity Log State
  const [activities, setActivities] = useState<any[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(false);

  // Proposal copy feedback
  const [copiedProposal, setCopiedProposal] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const statuses = [
    'DISCOVERED', 'VALIDATED', 'READY_TO_SEND', 'OUTREACH_SENT', 
    'RESPONDED', 'INTERESTED', 'REDIRECTED', 'OBJECTION', 
    'QUALIFIED', 'PROPOSAL_SENT', 'NEGOTIATING', 'CLOSED_WON', 'CLOSED_LOST'
  ];

  const origins = ['Google Maps', 'Instagram', 'Meta Ads Library', 'Facebook', 'Outro'];

  // Fetch initial leads and dashboard metrics
  const fetchData = async () => {
    setLoadingLeads(true);
    setLoadingMetrics(true);
    setError(null);
    const token = localStorage.getItem('admin_token');

    try {
      // 1. Fetch leads
      const leadsRes = await fetch(`${API_BASE}/crm/leads`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!leadsRes.ok) throw new Error('Falha ao buscar leads');
      const leadsData = await leadsRes.json();
      setLeads(leadsData);
      setLoadingLeads(false);

      // 2. Fetch metrics
      const metricsRes = await fetch(`${API_BASE}/crm/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
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

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Fetch conversation and activities for selected lead
  const handleSelectLead = async (lead: any) => {
    setSelectedLead(lead);
    setEditingLead({ ...lead });
    setUpdateSuccess(false);
    setMessages([]);
    setActivities([]);
    
    setLoadingMessages(true);
    setLoadingActivities(true);
    const token = localStorage.getItem('admin_token');

    try {
      // Fetch messages
      const msgRes = await fetch(`${API_BASE}/crm/conversations/${lead.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (msgRes.ok) {
        const msgData = await msgRes.json();
        setMessages(msgData);
      }
      setLoadingMessages(false);

      // Fetch activities
      const actRes = await fetch(`${API_BASE}/crm/leads/${lead.id}/activities`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (actRes.ok) {
        const actData = await actRes.json();
        setActivities(actData);
      }
      setLoadingActivities(false);
    } catch (err) {
      setLoadingMessages(false);
      setLoadingActivities(false);
    }
  };

  // Save Lead profile updates
  const handleSaveLeadDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLead) return;
    setUpdatingLead(true);
    setUpdateSuccess(false);
    const token = localStorage.getItem('admin_token');

    try {
      const res = await fetch(`${API_BASE}/crm/leads/${editingLead.id}`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify(editingLead)
      });
      if (!res.ok) throw new Error('Erro ao salvar dados do lead');
      const updatedLead = await res.json();
      
      // Update local state
      setLeads(leads.map(l => l.id === updatedLead.id ? updatedLead : l));
      setSelectedLead(updatedLead);
      setUpdateSuccess(true);
      
      // Refresh dashboard metrics in case status changed
      const metricsRes = await fetch(`${API_BASE}/crm/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (metricsRes.ok) {
        setMetrics(await metricsRes.json());
      }

      // Log event: status_changed or lead_updated
      const oldStatus = selectedLead.status;
      if (oldStatus !== updatedLead.status) {
        await logActivity(updatedLead.id, 'status_changed', { old_status: oldStatus, new_status: updatedLead.status });
      } else {
        await logActivity(updatedLead.id, 'lead_updated', {});
      }
    } catch (err: any) {
      alert(err.message || 'Erro ao salvar lead.');
    } finally {
      setUpdatingLead(false);
    }
  };

  // Helper to log activities
  const logActivity = async (leadId: string, eventType: string, metadata: any) => {
    const token = localStorage.getItem('admin_token');
    try {
      const res = await fetch(`${API_BASE}/crm/leads/${leadId}/activities`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ event_type: eventType, metadata })
      });
      if (res.ok) {
        const newAct = await res.json();
        setActivities(prev => [...prev, newAct]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Send WhatsApp message
  const handleSendWhatsapp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whatsappMessage.trim() || !selectedLead) return;
    setSendingMessage(true);
    const token = localStorage.getItem('admin_token');

    const payload = {
      lead_id: selectedLead.id,
      phone: selectedLead.whatsapp || '',
      message: whatsappMessage
    };

    try {
      const res = await fetch(`${API_BASE}/crm/messages/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Falha ao enviar mensagem');
      const newMsg = await res.json();
      
      // Update messages panel immediately
      setMessages([...messages, newMsg]);
      setWhatsappMessage('');

      // Update lead last interaction time in local list
      setLeads(leads.map(l => l.id === selectedLead.id ? { ...l, last_interaction: new Date().toISOString() } : l));

      // Append message_sent event to local activities list
      const timestamp = new Date().toISOString();
      const newAct = {
        lead_id: selectedLead.id,
        event_type: 'message_sent',
        timestamp,
        metadata: { message: newMsg.message, channel: 'whatsapp' }
      };
      setActivities([...activities, newAct]);

      // Refresh dashboard metrics
      const metricsRes = await fetch(`${API_BASE}/crm/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
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

    // 2. Log event
    await logActivity(selectedLead.id, 'proposal_opened', {});

    // 3. Open Instagram if available
    if (selectedLead.instagram) {
      window.open(selectedLead.instagram, '_blank');
    } else {
      alert('Texto da proposta copiado! Este lead não possui Instagram cadastrado.');
    }
  };

  // Filter leads locally
  const filteredLeads = leads.filter(lead => {
    const matchesStatus = statusFilter ? lead.status === statusFilter : true;
    const matchesOrigin = originFilter ? lead.origin === originFilter : true;
    
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = searchTerm 
      ? (lead.company_name?.toLowerCase().includes(searchLower) || 
         lead.email?.toLowerCase().includes(searchLower) ||
         lead.whatsapp?.includes(searchTerm) ||
         lead.responsible?.toLowerCase().includes(searchLower))
      : true;
      
    return matchesStatus && matchesOrigin && matchesSearch;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'CLOSED_WON': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'CLOSED_LOST': return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'NEGOTIATING': return 'bg-indigo-100 text-indigo-800 border-indigo-200';
      case 'PROPOSAL_SENT': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'RESPONDED': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'OUTREACH_SENT': return 'bg-blue-100 text-blue-800 border-blue-200';
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
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loadingMetrics ? (
          Array(4).fill(0).map((_, i) => (
            <div key={i} className="glass-card p-6 h-24 flex items-center justify-center animate-pulse">
              <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
            </div>
          ))
        ) : metrics ? (
          <>
            <div className="glass-card p-5 bg-white/70 border border-violet-100/30 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center text-purple-700">
                <Users className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Leads</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.total_leads}</p>
              </div>
            </div>

            <div className="glass-card p-5 bg-white/70 border border-violet-100/30 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center text-blue-700">
                <UserCheck className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Negociações</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.negociacoes}</p>
              </div>
            </div>

            <div className="glass-card p-5 bg-white/70 border border-violet-100/30 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700">
                <Check className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Clientes Fechados</p>
                <p className="text-2xl font-display font-extrabold text-slate-800">{metrics.clientes_fechados}</p>
              </div>
            </div>

            <div className="glass-card p-5 bg-white/70 border border-violet-100/30 flex items-center gap-4">
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
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
        {/* Leads Table Card */}
        <div className="xl:col-span-2 glass-card p-6 bg-white/70 border border-violet-100/30">
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
                {statuses.map(st => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>

              {/* Origin Filter */}
              <select
                value={originFilter}
                onChange={(e) => setOriginFilter(e.target.value)}
                className="px-3 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs font-semibold outline-none focus:border-purple-400 cursor-pointer"
              >
                <option value="">Origem (Todas)</option>
                {origins.map(or => (
                  <option key={or} value={or}>{or}</option>
                ))}
              </select>
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
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-violet-100/50 text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-2">ID</th>
                    <th className="py-3 px-2">Empresa</th>
                    <th className="py-3 px-2">WhatsApp</th>
                    <th className="py-3 px-2">Status</th>
                    <th className="py-3 px-2">Origem</th>
                    <th className="py-3 px-2">Última Interação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-violet-100/30 text-xs font-medium text-slate-600">
                  {filteredLeads.map((lead) => {
                    const isSelected = selectedLead?.id === lead.id;
                    return (
                      <tr 
                        key={lead.id} 
                        onClick={() => handleSelectLead(lead)}
                        className={`hover:bg-violet-50/30 cursor-pointer transition-colors ${
                          isSelected ? 'bg-purple-50/50 font-semibold' : ''
                        }`}
                      >
                        <td className="py-3.5 px-2 text-slate-400">#{lead.id}</td>
                        <td className="py-3.5 px-2 text-slate-800">{lead.company_name}</td>
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
            )}
          </div>
        </div>

        {/* Lead Details & Messaging Drawer */}
        <div className="glass-card bg-white/70 border border-violet-100/30 overflow-hidden">
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
                        onChange={(e) => setEditingLead({ ...editingLead, whatsapp: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Instagram URL</label>
                      <input
                        type="text"
                        value={editingLead.instagram || ''}
                        onChange={(e) => setEditingLead({ ...editingLead, instagram: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Email</label>
                      <input
                        type="text"
                        value={editingLead.email || ''}
                        onChange={(e) => setEditingLead({ ...editingLead, email: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</label>
                      <select
                        value={editingLead.status || 'DISCOVERED'}
                        onChange={(e) => setEditingLead({ ...editingLead, status: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                      >
                        {statuses.map(st => (
                          <option key={st} value={st}>{st}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Origem</label>
                      <select
                        value={editingLead.origin || 'Outro'}
                        onChange={(e) => setEditingLead({ ...editingLead, origin: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                      >
                        {origins.map(or => (
                          <option key={or} value={or}>{or}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Responsável</label>
                      <input
                        type="text"
                        value={editingLead.responsible || ''}
                        onChange={(e) => setEditingLead({ ...editingLead, responsible: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Texto Proposta</label>
                      <textarea
                        rows={1}
                        value={editingLead.proposal || ''}
                        onChange={(e) => setEditingLead({ ...editingLead, proposal: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none resize-none"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Observações</label>
                    <textarea
                      rows={2}
                      value={editingLead.notes || ''}
                      onChange={(e) => setEditingLead({ ...editingLead, notes: e.target.value })}
                      className="w-full px-3 py-1.5 rounded-lg border border-violet-100 bg-white/50 text-xs font-medium focus:border-purple-500 outline-none"
                    />
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
                <div className="h-48 overflow-y-auto border border-violet-100/50 rounded-xl p-3 bg-slate-50/50 flex flex-col gap-2.5">
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
                  <div ref={chatEndRef} />
                </div>

                {/* Chat Composer */}
                <form onSubmit={handleSendWhatsapp} className="flex gap-2 mt-3">
                  <input
                    type="text"
                    placeholder="Digite uma mensagem via WhatsApp..."
                    value={whatsappMessage}
                    onChange={(e) => setWhatsappMessage(e.target.value)}
                    disabled={sendingMessage}
                    className="flex-grow px-3.5 py-2 rounded-xl border border-violet-100 bg-white/50 text-xs font-semibold focus:border-purple-500 outline-none"
                  />
                  <button
                    type="submit"
                    disabled={sendingMessage || !whatsappMessage.trim()}
                    className="p-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center shadow-md shadow-emerald-600/10"
                  >
                    {sendingMessage ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                  </button>
                </form>
              </div>

              {/* Activity Log Timeline */}
              <div className="p-6">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3.5 flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-purple-600" />
                  Registro de Atividades
                </h4>

                <div className="space-y-4 max-h-48 overflow-y-auto pr-1">
                  {loadingActivities ? (
                    <div className="flex justify-center py-4">
                      <Loader2 className="w-4 h-4 text-purple-600 animate-spin" />
                    </div>
                  ) : activities.length === 0 ? (
                    <p className="text-[10px] text-slate-400 font-semibold text-center py-2">
                      Nenhuma atividade registrada para este lead.
                    </p>
                  ) : (
                    <div className="relative border-l border-violet-100 ml-2.5 space-y-4 text-[11px]">
                      {activities.map((act: any, i) => (
                        <div key={i} className="relative pl-6 group">
                          {/* Timeline dot */}
                          <span className="absolute -left-1.5 top-1 w-3 h-3 rounded-full border-2 border-purple-600 bg-white group-hover:bg-purple-600 transition-colors"></span>
                          
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-700 uppercase tracking-wide text-[10px]">
                              {act.event_type}
                            </span>
                            <span className="text-[9px] text-slate-400">{formatDate(act.timestamp)}</span>
                          </div>
                          
                          {/* Metadata formatting */}
                          {act.metadata && (
                            <p className="text-slate-500 mt-0.5 text-[10px] italic leading-tight">
                              {act.event_type === 'status_changed' && `Alterado de ${act.metadata.old_status} para ${act.metadata.new_status}`}
                              {act.event_type === 'message_sent' && `WhatsApp: "${act.metadata.message.substring(0, 30)}..."`}
                              {act.event_type === 'proposal_opened' && 'Proposta comercial copiada e Instagram aberto'}
                              {act.event_type === 'lead_created' && `Origem: ${act.metadata.origin || 'Robô scraper'}`}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
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

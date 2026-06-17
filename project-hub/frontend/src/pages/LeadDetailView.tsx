import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, MessageSquare, Send, Check, Clipboard, Loader2, 
  MessageCircle, AlertCircle, Trash2, Building2, Globe
} from 'lucide-react';
import { API_BASE, fetchWithAuth } from '../services/api';

export default function LeadDetailView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [lead, setLead] = useState<any>(null);
  const [editingLead, setEditingLead] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form saving states
  const [updatingLead, setUpdatingLead] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [deletingLead, setDeletingLead] = useState(false);

  // Chat & Messaging state
  const [messages, setMessages] = useState<any[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [whatsappMessage, setWhatsappMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
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

  const fetchLeadMessages = async (showLoading = false) => {
    if (showLoading) setLoadingMessages(true);
    try {
      const msgRes = await fetchWithAuth(`${API_BASE}/crm/conversations/${id}`);
      if (msgRes.ok) {
        const msgData = await msgRes.json();
        setMessages(msgData);
      }
    } catch (err) {
      console.error('Erro ao buscar mensagens do lead:', err);
    } finally {
      if (showLoading) setLoadingMessages(false);
    }
  };

  const fetchLeadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch single lead
      const res = await fetchWithAuth(`${API_BASE}/crm/leads/${id}`);
      if (!res.ok) throw new Error('Falha ao carregar os dados do lead');
      const leadData = await res.json();
      setLead(leadData);
      setEditingLead({ ...leadData });

      // 2. Fetch messages for the lead
      await fetchLeadMessages(true);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar o lead.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeadData();
  }, [id]);

  useEffect(() => {
    if (!id) return;
    const token = localStorage.getItem("admin_token");
    if (!token) return;

    const sseUrl = `${API_BASE}/webhooks/events/leads/${id}?token=${encodeURIComponent(token)}`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      if (event.data === 'reload') {
        fetchLeadMessages(false);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
    };

    return () => {
      eventSource.close();
    };
  }, [id]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleFieldChange = (field: string, value: string) => {
    if (!editingLead) return;
    const updated = { ...editingLead, [field]: value };
    
    // Recalculate origin method based on priority
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
      
      setLead(updatedLead);
      setUpdateSuccess(true);
      setTimeout(() => setUpdateSuccess(false), 3000);
    } catch (err: any) {
      alert(err.message || 'Erro ao salvar o lead.');
    } finally {
      setUpdatingLead(false);
    }
  };

  const handleDeleteLead = async () => {
    if (!window.confirm('Tem certeza de que deseja excluir este lead? O lead será removido permanentemente.')) return;
    setDeletingLead(true);

    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/leads/${id}`, {
        method: 'DELETE'
      });
      if (!res.ok) throw new Error('Erro ao excluir o lead');
      
      alert('Lead excluído com sucesso!');
      navigate('/crm');
    } catch (err: any) {
      alert(err.message || 'Erro ao excluir o lead.');
    } finally {
      setDeletingLead(false);
    }
  };

  const handleSendWhatsapp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whatsappMessage.trim() || !lead) return;
    setSendingMessage(true);

    const payload = {
      lead_id: lead.id,
      phone: lead.whatsapp || '',
      message: whatsappMessage
    };

    try {
      const res = await fetchWithAuth(`${API_BASE}/crm/messages/send`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Falha ao enviar mensagem');
      const newMsg = await res.json();
      
      setMessages([...messages, newMsg]);
      setWhatsappMessage('');

      // Update status locally if it was Prospectado
      setLead((prev: any) => {
        const updated = { ...prev, last_interaction: new Date().toISOString(), mensagem_enviada: true };
        if (prev.status === 'Prospectado') {
          updated.status = 'Abordagem Enviada';
        }
        return updated;
      });

      if (lead.status === 'Prospectado') {
        await fetchWithAuth(`${API_BASE}/crm/leads/${lead.id}`, {
          method: 'PUT',
          body: JSON.stringify({ ...lead, status: 'Abordagem Enviada', mensagem_enviada: true })
        });
      }
    } catch (err: any) {
      alert(err.message || 'Erro ao enviar mensagem.');
    } finally {
      setSendingMessage(false);
    }
  };

  const handleSendProposal = async () => {
    if (!lead || !lead.proposal) return;
    
    // Copy proposal text
    navigator.clipboard.writeText(lead.proposal);
    setCopiedProposal(true);
    setTimeout(() => setCopiedProposal(false), 2000);

    // Open Instagram DM if available
    if (lead.instagram) {
      let username = lead.instagram.trim();
      if (username.startsWith('@')) username = username.substring(1);
      if (username.includes('instagram.com/')) {
        const parts = username.split('instagram.com/');
        username = parts[parts.length - 1].split('/')[0].split('?')[0];
      }
      window.open(`https://ig.me/m/${username}`, '_blank');
    } else {
      alert('Texto da proposta copiado! Este lead não possui Instagram cadastrado.');
    }

    // Auto-advance status if Prospectado
    if (lead.status === 'Prospectado') {
      setLead((prev: any) => ({ ...prev, status: 'Abordagem Enviada', mensagem_enviada: true }));
      await fetchWithAuth(`${API_BASE}/crm/leads/${lead.id}`, {
        method: 'PUT',
        body: JSON.stringify({ ...lead, status: 'Abordagem Enviada', mensagem_enviada: true })
      });
    }
  };

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

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
        <p className="text-sm font-semibold text-slate-500">Carregando informações do lead...</p>
      </div>
    );
  }

  if (error || !lead || !editingLead) {
    return (
      <div className="max-w-xl mx-auto my-12 p-6 glass-card border border-rose-100/50 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-800">Falha ao Abrir Ficha</h2>
        <p className="text-sm text-slate-500">{error || 'Lead não encontrado no banco de dados.'}</p>
        <button 
          onClick={() => navigate('/crm')}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition-all cursor-pointer inline-flex items-center gap-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Voltar ao CRM
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header View */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/crm')}
            className="p-2.5 rounded-xl border border-violet-100 bg-white hover:bg-violet-50 text-slate-600 transition-all cursor-pointer shadow-sm"
            title="Voltar ao CRM"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl font-display font-extrabold text-slate-800 flex items-center gap-2">
              {lead.company_name}
              <span className={`px-2.5 py-0.5 rounded-full border text-[10px] uppercase font-bold tracking-wide ${getStatusColor(lead.status)}`}>
                {lead.status}
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5 font-medium">ID do Lead: #{lead.id}</p>
          </div>
        </div>

        {lead.proposal && (
          <button
            onClick={handleSendProposal}
            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-bold transition-all cursor-pointer shadow-sm shadow-purple-200/50"
          >
            {copiedProposal ? (
              <>
                <Check className="w-3.5 h-3.5 animate-bounce" />
                <span>Proposta Comercial Copiada!</span>
              </>
            ) : (
              <>
                <Clipboard className="w-3.5 h-3.5" />
                <span>Copiar e Enviar Proposta Comercial</span>
              </>
            )}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Profile Form Details */}
        <div className="lg:col-span-7 glass-card p-6 bg-white/70 border border-violet-100/30">
          <h2 className="text-md font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-purple-600" />
            Ficha Detalhada do Lead
          </h2>

          <form onSubmit={handleSaveLeadDetails} className="space-y-4">
            {/* Grid 1: Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Nome da Empresa</label>
                <input
                  type="text"
                  value={editingLead.company_name || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, company_name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">WhatsApp</label>
                <input
                  type="text"
                  value={editingLead.whatsapp || ''}
                  onChange={(e) => handleFieldChange('whatsapp', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
            </div>

            {/* Grid 2: Digital Channels */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">E-mail</label>
                <input
                  type="email"
                  value={editingLead.email || ''}
                  onChange={(e) => handleFieldChange('email', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Instagram</label>
                <input
                  type="text"
                  value={editingLead.instagram || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, instagram: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
            </div>

            {/* Grid 3: Niche and Status */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Nicho / Segmento</label>
                <input
                  type="text"
                  value={editingLead.segmento || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, segmento: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Status na Esteira</label>
                <select
                  value={editingLead.status || 'Prospectado'}
                  onChange={(e) => setEditingLead({ ...editingLead, status: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                >
                  {statuses.map(st => (
                    <option key={st} value={st}>{st}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Grid 4: Lead Classification */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-3 border-t border-slate-100/50">
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Score</label>
                <input
                  type="text"
                  value={editingLead.score || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, score: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Temperatura</label>
                <input
                  type="text"
                  value={editingLead.temperatura || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, temperatura: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Localização</label>
                <input
                  type="text"
                  value={editingLead.localizacao || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, localizacao: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">LID</label>
                <input
                  type="text"
                  value={editingLead.lid || ''}
                  onChange={(e) => setEditingLead({ ...editingLead, lid: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                />
              </div>
            </div>

            {/* Grid 5: Site Diagnostics */}
            <div className="pt-3 border-t border-slate-100/50 space-y-4">
              <h4 className="text-[11px] font-bold text-purple-700 uppercase tracking-wide flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5" />
                Presença Digital & Site
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">URL Site</label>
                  <input
                    type="text"
                    value={editingLead.url_site || ''}
                    onChange={(e) => setEditingLead({ ...editingLead, url_site: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Possui Site Próprio</label>
                  <select
                    value={editingLead.tem_site_proprio !== undefined && editingLead.tem_site_proprio !== null ? String(editingLead.tem_site_proprio) : 'false'}
                    onChange={(e) => setEditingLead({ ...editingLead, tem_site_proprio: e.target.value === 'true' })}
                    className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                  >
                    <option value="true">Sim</option>
                    <option value="false">Não</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Possui Chamada para Ação (CTA)</label>
                  <select
                    value={editingLead.tem_cta || 'não'}
                    onChange={(e) => setEditingLead({ ...editingLead, tem_cta: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                  >
                    <option value="sim">Sim</option>
                    <option value="não">Não</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Formulário de Captação</label>
                  <select
                    value={editingLead.tem_formulario || 'não'}
                    onChange={(e) => setEditingLead({ ...editingLead, tem_formulario: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none cursor-pointer"
                  >
                    <option value="sim">Sim</option>
                    <option value="não">Não</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">ID Anúncio Meta</label>
                  <input
                    type="text"
                    value={editingLead.id_anuncio_meta || ''}
                    onChange={(e) => setEditingLead({ ...editingLead, id_anuncio_meta: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Erros Identificados no Site</label>
                  <input
                    type="text"
                    value={editingLead.erros_identificados_site || ''}
                    onChange={(e) => setEditingLead({ ...editingLead, erros_identificados_site: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-semibold focus:border-purple-500 outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Proposal / Text diagnostics */}
            <div className="pt-3 border-t border-slate-100/50 space-y-2">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Proposta Inicial / Diagnóstico Completo</label>
              <textarea
                rows={4}
                value={editingLead.proposta_inicial || ''}
                onChange={(e) => setEditingLead({ ...editingLead, proposta_inicial: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-violet-100 bg-white text-xs font-medium focus:border-purple-500 outline-none resize-y min-h-[100px]"
              />
            </div>

            {/* Signature / Audit Trail */}
            {(lead.created_by || lead.updated_by || lead.alterado_por || editingLead.created_by || editingLead.updated_by || editingLead.alterado_por) && (
              <div className="text-[10px] text-slate-400 font-semibold flex items-center justify-between gap-4 pt-2.5 pb-1 border-t border-dashed border-slate-200">
                {(lead.created_by || editingLead.created_by) && (
                  <span>Criado por: <span className="text-slate-500 font-bold">{lead.created_by || editingLead.created_by}</span></span>
                )}
                {(lead.updated_by || lead.alterado_por || editingLead.updated_by || editingLead.alterado_por) && (
                  <span className="ml-auto">Última alteração: <span className="text-slate-500 font-bold">{lead.updated_by || lead.alterado_por || editingLead.updated_by || editingLead.alterado_por}</span></span>
                )}
              </div>
            )}

            {/* Form Actions */}
            <div className="flex items-center justify-between gap-4 pt-4 border-t border-slate-100/50">
              <div className="flex-grow">
                {updateSuccess && (
                  <p className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                    <Check className="w-4 h-4" /> Alterações salvas com sucesso!
                  </p>
                )}
              </div>
              
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleDeleteLead}
                  disabled={updatingLead || deletingLead}
                  className="px-4 py-2 bg-rose-50 border border-rose-200 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                >
                  {deletingLead ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                  Excluir Lead
                </button>

                <button
                  type="submit"
                  disabled={updatingLead || deletingLead}
                  className="px-5 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                >
                  {updatingLead && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Salvar Alterações
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Right Column: Integrated Chat and messaging panel */}
        <div className="lg:col-span-5 glass-card bg-white/70 border border-violet-100/30 overflow-hidden flex flex-col min-h-[600px]">
          <div className="p-6 border-b border-violet-100/30">
            <h3 className="text-md font-bold text-slate-800 flex items-center gap-2">
              <MessageCircle className="w-4 h-4 text-emerald-500" />
              Chat Comercial Integrado
            </h3>
            <p className="text-xs text-slate-400 mt-1 font-medium">Histórico de conversas via WhatsApp/Instagram</p>
          </div>

          {/* Messages Panel Container */}
          <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/30 min-h-[350px] max-h-[450px]">
            {loadingMessages ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-purple-600 animate-spin" />
              </div>
            ) : messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
                <MessageSquare className="w-8 h-8 opacity-40" />
                <p className="text-xs font-semibold">Nenhuma mensagem registrada.</p>
              </div>
            ) : (
              messages.map((msg: any, i) => {
                const isUser = msg.sender === 'user';
                return (
                  <div 
                    key={msg.id || i}
                    className={`max-w-[85%] rounded-2xl p-3 text-xs ${
                      isUser 
                        ? 'bg-purple-600 text-white self-end rounded-tr-none ml-auto' 
                        : 'bg-white text-slate-800 border border-slate-100 self-start mr-auto rounded-tl-none shadow-sm'
                    }`}
                  >
                    <p className="font-medium leading-relaxed break-words whitespace-pre-wrap">{msg.message}</p>
                    <div className={`text-[9px] mt-1.5 flex items-center gap-1 justify-end ${isUser ? 'text-purple-200' : 'text-slate-400 font-semibold'}`}>
                      <span>{msg.channel === 'whatsapp' ? 'WhatsApp' : 'Instagram'}</span>
                      <span>•</span>
                      <span>{formatDate(msg.timestamp)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Message Composer Area */}
          <div className="p-4 border-t border-violet-100/30 bg-white/70">
            <form onSubmit={handleSendWhatsapp} className="flex gap-2 items-end">
              <textarea
                placeholder="Digite a mensagem para enviar via WhatsApp... (Pressione Enter para enviar, Shift+Enter para nova linha)"
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
                className="flex-grow px-3 py-2 rounded-xl border border-violet-100 bg-white text-xs font-medium focus:border-purple-500 outline-none resize-none min-h-[60px] max-h-[120px]"
              />
              <button
                type="submit"
                disabled={sendingMessage || !whatsappMessage.trim()}
                className="p-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center shadow-md shadow-emerald-600/10 h-10 w-10 flex-shrink-0"
              >
                {sendingMessage ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

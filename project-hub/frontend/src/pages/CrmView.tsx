import { useState, useEffect, useMemo } from 'react';
import { 
  Users, UserCheck, MessageSquare, Check, 
  Search, Loader2, Sparkles, MessageCircle, AlertCircle,
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

      // Sort leads: by last_interaction descending
      const sortedLeads = [...leadsData].sort((a: any, b: any) => {
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

    // Sort: by last_interaction descending
    return filtered.sort((a, b) => {
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

      {/* Main CRM Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Leads Table Card */}
        <div className="xl:col-span-12 glass-card p-6 bg-white/70 border border-violet-100/30">
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
                      return (
                        <tr 
                          key={lead.id} 
                          onClick={() => window.open(`/crm/leads/${lead.id}`, '_blank')}
                          className="hover:bg-violet-50/30 cursor-pointer transition-colors"
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

      </div>
    </div>
  );
}

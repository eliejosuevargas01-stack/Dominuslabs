/**
 * Documentation-Driven Testing:
 * O comportamento esperado para AdminDashboard.tsx:
 * - Botão 'Novo Projeto': Exibe modal de cadastro com loading na submissão.
 * - Renderiza listagens, filtragem de buscas de projetos e aciona toasts via `Sonner`.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchProjects, createProject, API_BASE, getUserRole, deleteProject } from '../services/api';
import { 
  Folder, 
  Layers, 
  CheckCircle, 
  DollarSign, 
  TrendingUp, 
  Plus, 
  ExternalLink, 
  Globe, 
  Loader2, 
  X,
  FileCode2,
  Trash2
} from 'lucide-react';

const GithubIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    width="24"
    height="24"
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
  </svg>
);

export default function AdminDashboard() {
  const isViewer = getUserRole() === 'viewer';
  const isAdmin = getUserRole() === 'admin';
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const handleDeleteProject = async (id: number, name: string) => {
    if (!window.confirm(`Tem certeza que deseja excluir o projeto "${name}"? Esta ação não pode ser desfeita e removerá todas as tarefas, deploys e commits associados.`)) {
      return;
    }
    try {
      setError('');
      await deleteProject(id);
      loadDashboardData();
    } catch (err: any) {
      console.error(err);
      setError('Erro ao excluir o projeto.');
    }
  };
  
  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    client_name: '',
    description: '',
    project_type: 'Landing Page',
    value: '',
    status: 'NEW',
    github_url: '',
    deploy_url: ''
  });

  const loadDashboardData = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const data = await fetchProjects();
      setProjects(data);
      setError('');
    } catch (err: any) {
      console.error(err);
      setError('Erro ao carregar os projetos. Verifique se o backend está ativo.');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();

    const eventSource = new EventSource(`${API_BASE}/webhooks/events`);
    eventSource.onmessage = (event) => {
      if (event.data === 'reload') {
        loadDashboardData(true);
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.client_name || !formData.value) return;

    try {
      setSubmitting(true);
      const payload = {
        ...formData,
        value: Number(formData.value),
        github_url: formData.github_url.trim() || null,
        deploy_url: formData.deploy_url.trim() || null,
        description: formData.description.trim() || null
      };
      
      await createProject(payload);
      setModalOpen(false);
      setFormData({
        name: '',
        client_name: '',
        description: '',
        project_type: 'Landing Page',
        value: '',
        status: 'NEW',
        github_url: '',
        deploy_url: ''
      });
      loadDashboardData();
    } catch (err) {
      console.error(err);
      setError('Erro ao criar projeto. Verifique os campos.');
    } finally {
      setSubmitting(false);
    }
  };

  // KPIs
  const totalProjects = projects.length;
  const activeProjects = projects.filter(p => p.status !== 'DELIVERED').length;
  const completedProjects = projects.filter(p => p.status === 'DELIVERED').length;
  const totalRevenue = projects.reduce((acc, p) => acc + p.value, 0);
  
  // Calculate current month's revenue (mock date-based logic or just all DELIVERED/DEPLOYED values)
  const currentMonthRevenue = projects
    .filter(p => p.status === 'DELIVERED' || p.status === 'DEPLOYED')
    .reduce((acc, p) => acc + p.value, 0);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <Loader2 className="w-10 h-10 text-purple-600 animate-spin" />
        <p className="text-zinc-500 font-medium">Carregando workstation...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-[fade-in_0.4s_ease-out]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-semibold tracking-tight text-zinc-900 md:text-4xl">
            Dashboard de Projetos
          </h1>
          <p className="text-zinc-500 text-sm mt-1">
            Gerencie suas landing pages, automações e deploys de clientes.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="btn-primary inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm transition-all duration-200 self-start md:self-auto cursor-pointer"
        >
          <Plus className="w-5 h-5" />
          Novo Projeto
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-red-700 text-sm font-medium">
          {error}
        </div>
      )}

      {/* KPI Section */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
        <div className="surface-card p-5 relative overflow-hidden group">
          <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-purple-700 mb-4">
            <Folder className="w-5 h-5" />
          </div>
          <p className="text-zinc-500 text-[11px] font-semibold uppercase tracking-wider">Total de Projetos</p>
          <p className="text-3xl font-bold text-zinc-900 mt-1">{totalProjects}</p>
        </div>

        <div className="surface-card p-5 relative overflow-hidden group">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-700 mb-4">
            <Layers className="w-5 h-5" />
          </div>
          <p className="text-zinc-500 text-[11px] font-semibold uppercase tracking-wider">Projetos Ativos</p>
          <p className="text-3xl font-bold text-zinc-900 mt-1">{activeProjects}</p>
        </div>

        <div className="surface-card p-5 relative overflow-hidden group">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-700 mb-4">
            <CheckCircle className="w-5 h-5" />
          </div>
          <p className="text-zinc-500 text-[11px] font-semibold uppercase tracking-wider">Concluídos</p>
          <p className="text-3xl font-bold text-zinc-900 mt-1">{completedProjects}</p>
        </div>

        <div className="surface-card p-5 relative overflow-hidden group">
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-700 mb-4">
            <DollarSign className="w-5 h-5" />
          </div>
          <p className="text-zinc-500 text-[11px] font-semibold uppercase tracking-wider">Receita Total</p>
          <p className="text-3xl font-bold text-zinc-900 mt-1">R$ {totalRevenue.toLocaleString()}</p>
        </div>

        <div className="surface-card p-5 relative overflow-hidden group border-emerald-200 bg-emerald-50/50">
          <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700 mb-4">
            <TrendingUp className="w-5 h-5" />
          </div>
          <p className="text-zinc-500 text-[11px] font-semibold uppercase tracking-wider">Receita Mês</p>
          <p className="text-3xl font-bold text-emerald-700 mt-1">R$ {currentMonthRevenue.toLocaleString()}</p>
        </div>
      </div>

      {/* Projects Table Container */}
      <div className="surface-card overflow-hidden">
        <div className="p-6 border-b border-zinc-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-zinc-900 flex items-center gap-2">
            <FileCode2 className="w-5 h-5 text-purple-600" />
            Todos os Projetos
          </h2>
          <span className="text-[11px] font-medium text-zinc-500 bg-zinc-100 border border-zinc-200 px-3 py-1 rounded-full self-start sm:self-auto">
            {projects.length} {projects.length === 1 ? 'projeto encontrado' : 'projetos encontrados'}
          </span>
        </div>

        {projects.length === 0 ? (
          <div className="p-12 text-center">
            <Folder className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
            <h3 className="text-base font-semibold text-zinc-800">Nenhum projeto cadastrado</h3>
            <p className="text-zinc-500 text-sm mt-1 max-w-sm mx-auto">
              Comece criando seu primeiro projeto clicando no botão "Novo Projeto" acima.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className=" border-b border-zinc-100 text-zinc-500 text-[11px] font-semibold uppercase tracking-wider">
                  <th className="p-4 pl-6">Nome do Projeto</th>
                  <th className="p-4">Cliente</th>
                  <th className="p-4">Valor</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Links rápidos</th>
                  <th className="p-4 pr-6 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100/60 text-sm">
                {projects.map(p => {
                  const statusColors: any = {
                    NEW: 'bg-blue-50 text-blue-700 border-blue-200/50',
                    IN_PROGRESS: 'bg-purple-50 text-purple-700 border-purple-200/50',
                    REVIEW: 'bg-amber-50 text-amber-800 border-amber-200/50',
                    DEPLOYED: 'bg-emerald-50 text-emerald-800 border-emerald-200/50',
                    DELIVERED: 'bg-emerald-100 text-emerald-900 border-emerald-300/50'
                  };

                  return (
                    <tr key={p.id} className="hover: transition-colors group">
                      <td className="p-4 pl-6">
                        <Link to={`/project-hub/project/${p.id}`} className="font-semibold text-zinc-900 hover:text-purple-600 transition-colors">
                          {p.name}
                        </Link>
                        <span className="block text-[11px] text-zinc-500 mt-0.5">{p.project_type}</span>
                      </td>
                      <td className="p-4 font-medium text-zinc-700">{p.client_name}</td>
                      <td className="p-4 font-semibold text-zinc-900">R$ {p.value.toLocaleString()}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${statusColors[p.status] || 'bg-zinc-100 text-zinc-700'}`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          {p.github_url ? (
                            <a href={p.github_url} target="_blank" rel="noopener noreferrer" className="text-zinc-400 hover:text-zinc-900" title="Repo GitHub">
                              <GithubIcon className="w-4 h-4" />
                            </a>
                          ) : (
                            <span className="w-4 h-4 block"></span>
                          )}
                          {p.deploy_url ? (
                            <a href={p.deploy_url} target="_blank" rel="noopener noreferrer" className="text-zinc-400 hover:text-zinc-900" title="Deploy Link">
                              <Globe className="w-4 h-4" />
                            </a>
                          ) : (
                            <span className="w-4 h-4 block"></span>
                          )}
                          <Link to={`/project/${p.public_token}`} className="text-zinc-400 hover:text-purple-600 flex items-center gap-1 text-[11px] font-medium" title="Link do Cliente">
                            <ExternalLink className="w-3 h-3" />
                            Público
                          </Link>
                        </div>
                      </td>
                      <td className="p-4 pr-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            to={`/project-hub/project/${p.id}`}
                            className="text-[11px] font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 px-3 py-1.5 rounded-lg border border-zinc-200 transition-all inline-block"
                          >
                            {isViewer ? 'Visualizar' : 'Gerenciar'}
                          </Link>
                          {isAdmin && (
                            <button
                              onClick={() => handleDeleteProject(p.id, p.name)}
                              className="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-all cursor-pointer inline-flex items-center justify-center border border-transparent hover:border-red-100"
                              title="Excluir Projeto"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Creation Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4   animate-[fade-in_0.2s_ease-out]">
          <div className="bg-white rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl border border-zinc-200 flex flex-col max-h-[90vh] animate-[scale-up_0.25s_cubic-bezier(0.34,1.56,0.64,1)]">
            
            {/* Modal Header */}
            <div className="p-5 border-b border-zinc-100 flex items-center justify-between ">
              <div>
                <h3 className="text-lg font-semibold text-zinc-900">Novo Projeto</h3>
                <p className="text-xs text-zinc-500 mt-0.5">Preencha os dados básicos para iniciar o projeto.</p>
              </div>
              <button 
                onClick={() => setModalOpen(false)}
                className="p-1.5 rounded-lg hover:bg-zinc-200 text-zinc-400 hover:text-zinc-700 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Nome do Projeto *</label>
                  <input
                    type="text"
                    name="name"
                    required
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="ex: Clínica Odontológica Marcos"
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  />
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Nome do Cliente *</label>
                  <input
                    type="text"
                    name="client_name"
                    required
                    value={formData.client_name}
                    onChange={handleInputChange}
                    placeholder="ex: Marcos Silva"
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Tipo de Projeto</label>
                  <select
                    name="project_type"
                    value={formData.project_type}
                    onChange={handleInputChange}
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  >
                    <option value="Landing Page">Landing Page</option>
                    <option value="Automação">Automação</option>
                    <option value="Web App">Web App</option>
                    <option value="Design/Figma">Design/Figma</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Valor (R$) *</label>
                  <input
                    type="number"
                    name="value"
                    required
                    value={formData.value}
                    onChange={handleInputChange}
                    placeholder="ex: 500"
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Status Inicial</label>
                  <select
                    name="status"
                    value={formData.status}
                    onChange={handleInputChange}
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  >
                    <option value="NEW">NEW</option>
                    <option value="IN_PROGRESS">IN PROGRESS</option>
                    <option value="REVIEW">REVIEW</option>
                    <option value="DEPLOYED">DEPLOYED</option>
                    <option value="DELIVERED">DELIVERED</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Descrição</label>
                <textarea
                  name="description"
                  rows={3}
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Mais informações sobre o escopo do projeto..."
                  className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                    <GithubIcon className="w-3.5 h-3.5 text-zinc-400" />
                    GitHub URL (opcional)
                  </label>
                  <input
                    type="url"
                    name="github_url"
                    value={formData.github_url}
                    onChange={handleInputChange}
                    placeholder="https://github.com/usuario/repositorio"
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-zinc-400" />
                    Deploy URL (opcional)
                  </label>
                  <input
                    type="url"
                    name="deploy_url"
                    value={formData.deploy_url}
                    onChange={handleInputChange}
                    placeholder="https://projeto.netlify.app"
                    className="w-full text-sm border border-zinc-200 rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  />
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center justify-end gap-3 pt-5 border-t border-zinc-100">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="btn-secondary px-5 py-2.5 rounded-lg text-sm cursor-pointer"
                  disabled={submitting}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary px-5 py-2.5 rounded-lg text-sm flex items-center gap-2 cursor-pointer"
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Criando...
                    </>
                  ) : (
                    'Criar Projeto'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scale-up {
          from { transform: scale(0.95); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
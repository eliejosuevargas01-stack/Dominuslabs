import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  fetchProject, 
  updateProject, 
  fetchAssets, 
  uploadAsset, 
  fetchCommits, 
  fetchDeploys,
  fetchTasks,
  API_BASE
} from '../services/api';
import ProgressBar from '../components/ProgressBar';
import TaskChecklist from '../components/TaskChecklist';
import { 
  ArrowLeft, 
  Edit3, 
  UploadCloud, 
  FileText, 
  Image as ImageIcon, 
  Video, 
  Music, 
  Globe, 
  Link as LinkIcon, 
  Calendar, 
  DollarSign, 
  CheckSquare, 
  Activity, 
  Loader2, 
  Download,
  X,
  Lock,
  Sparkles
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

const API_BASE_URL = API_BASE;

export default function AdminProjectView() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<any>(null);
  const [assets, setAssets] = useState<any[]>([]);
  const [commits, setCommits] = useState<any[]>([]);
  const [deploys, setDeploys] = useState<any[]>([]);
  const [progress, setProgress] = useState(0);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [editForm, setEditForm] = useState({
    name: '',
    client_name: '',
    description: '',
    project_type: '',
    value: '',
    status: '',
    github_url: '',
    deploy_url: ''
  });

  // File Upload State
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const loadProjectData = useCallback(async () => {
    if (!id) return;
    try {
      const projData = await fetchProject(id);
      setProject(projData);
      
      // Load form values
      setEditForm({
        name: projData.name || '',
        client_name: projData.client_name || '',
        description: projData.description || '',
        project_type: projData.project_type || '',
        value: String(projData.value) || '',
        status: projData.status || 'NEW',
        github_url: projData.github_url || '',
        deploy_url: projData.deploy_url || ''
      });

      // Fetch auxiliary data
      const [assetsData, commitsData, deploysData, tasksData] = await Promise.all([
        fetchAssets(id),
        fetchCommits(id),
        fetchDeploys(id),
        fetchTasks(id)
      ]);

      setAssets(assetsData);
      setCommits(commitsData);
      setDeploys(deploysData);

      // Compute progress
      if (tasksData && tasksData.length > 0) {
        const completed = tasksData.filter((t: any) => t.status === 'DONE').length;
        setProgress((completed / tasksData.length) * 100);
      } else {
        setProgress(0);
      }

      setError('');
    } catch (err: any) {
      console.error(err);
      setError('Erro ao carregar detalhes do projeto.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    setLoading(true);
    loadProjectData();
  }, [loadProjectData]);

  const handleEditChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setEditForm(prev => ({ ...prev, [name]: value }));
  };

  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

    try {
      setUpdating(true);
      const payload = {
        ...editForm,
        value: Number(editForm.value),
        github_url: editForm.github_url.trim() || null,
        deploy_url: editForm.deploy_url.trim() || null,
        description: editForm.description.trim() || null
      };

      const updated = await updateProject(id, payload);
      setProject(updated);
      setEditOpen(false);
      loadProjectData();
    } catch (err) {
      console.error(err);
      setError('Erro ao atualizar projeto.');
    } finally {
      setUpdating(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !id) return;

    try {
      setUploading(true);
      setUploadError('');
      await uploadAsset(id, files[0]);
      
      // Reload assets
      const assetsData = await fetchAssets(id);
      setAssets(assetsData);
    } catch (err) {
      console.error(err);
      setUploadError('Falha no upload do arquivo.');
    } finally {
      setUploading(false);
    }
  };

  const formatBytes = (bytes: number, decimals = 2) => {
    if (!+bytes) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'images': return <ImageIcon className="w-5 h-5 text-emerald-500" />;
      case 'videos': return <Video className="w-5 h-5 text-indigo-500" />;
      case 'audio': return <Music className="w-5 h-5 text-amber-500" />;
      default: return <FileText className="w-5 h-5 text-slate-500" />;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <Loader2 className="w-10 h-10 text-violet-600 animate-spin" />
        <p className="text-slate-500 font-medium">Carregando detalhes do projeto...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Projeto não encontrado.</p>
        <Link to="/project-hub" className="text-violet-600 font-bold hover:underline mt-4 inline-block">Voltar ao dashboard</Link>
      </div>
    );
  }

  const clientPublicUrl = `${window.location.origin}/project/${project.public_token}`;

  return (
    <div className="space-y-6 pb-12 animate-[fade-in_0.3s_ease-out]">
      {/* Header action bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <Link to="/project-hub" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-violet-600 transition-colors self-start">
          <ArrowLeft className="w-4 h-4" />
          Voltar ao Dashboard
        </Link>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setEditOpen(true)}
            className="btn-secondary flex items-center gap-2 px-4 py-2 rounded-xl text-sm cursor-pointer"
          >
            <Edit3 className="w-4 h-4" />
            Editar Detalhes
          </button>
          <a
            href={clientPublicUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary flex items-center gap-2 px-4 py-2 rounded-xl text-sm cursor-pointer"
          >
            <LinkIcon className="w-4 h-4" />
            Visualizar Página do Cliente
          </a>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-2xl text-rose-700 text-sm font-medium">
          {error}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left column: Summary & Configs */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card p-6 space-y-6">
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-violet-100 text-violet-700 border border-violet-200">
                  {project.project_type}
                </span>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  {project.status}
                </span>
              </div>
              <h1 className="text-3xl font-extrabold text-slate-900 mt-3">{project.name}</h1>
              <p className="text-slate-500 text-sm mt-1.5 font-medium">Cliente: {project.client_name}</p>
            </div>

            {project.description && (
              <div className="border-t border-slate-100/80 pt-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Descrição / Escopo</h3>
                <p className="text-sm text-slate-600 leading-relaxed break-words">{project.description}</p>
              </div>
            )}

            {/* Meta values list */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-slate-100/80 pt-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100/50">
                  <DollarSign className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider">Investimento</p>
                  <p className="text-sm font-bold text-slate-900">R$ {project.value.toLocaleString()}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-violet-50 text-violet-700 flex items-center justify-center border border-violet-100/50">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider">Criado em</p>
                  <p className="text-sm font-semibold text-slate-700">{new Date(project.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center border border-amber-100/50">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider">Última alteração</p>
                  <p className="text-sm font-semibold text-slate-700">{new Date(project.updated_at).toLocaleDateString()}</p>
                </div>
              </div>
            </div>

            {/* Links integration */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-slate-100/80">
              <div className="flex-1 p-3 bg-slate-50/50 border border-slate-100 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5 min-w-0">
                  <GithubIcon className="w-5 h-5 text-slate-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">GitHub Repo</p>
                    {project.github_url ? (
                      <a href={project.github_url} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-violet-600 hover:underline truncate block">
                        {project.github_url}
                      </a>
                    ) : (
                      <span className="text-xs text-slate-400 italic">Não configurado</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex-1 p-3 bg-slate-50/50 border border-slate-100 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5 min-w-0">
                  <Globe className="w-5 h-5 text-slate-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Deploy Preview</p>
                    {project.deploy_url ? (
                      <a href={project.deploy_url} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-violet-600 hover:underline truncate block">
                        {project.deploy_url}
                      </a>
                    ) : (
                      <span className="text-xs text-slate-400 italic">Não configurado</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Client public link copy card */}
            <div className="p-4 bg-amber-50/70 border border-amber-100 rounded-2xl flex items-center gap-3">
              <Lock className="w-5 h-5 text-amber-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">Link de acompanhamento do cliente (Público)</p>
                <input
                  type="text"
                  readOnly
                  value={clientPublicUrl}
                  onClick={(e) => (e.target as HTMLInputElement).select()}
                  className="w-full text-xs bg-white/70 border border-amber-200/60 rounded-lg px-2.5 py-1.5 focus:outline-none text-slate-600 cursor-pointer font-mono mt-1"
                />
              </div>
            </div>

            {/* Webhook Github card */}
            <div className="p-4 bg-violet-50/70 border border-violet-100 rounded-2xl flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-violet-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-bold text-violet-800 uppercase tracking-wider">Webhook de Integração GitHub (Exclusivo do Projeto)</p>
                <input
                  type="text"
                  readOnly
                  value={`${API_BASE_URL}/webhooks/github/${project.public_token}`}
                  onClick={(e) => (e.target as HTMLInputElement).select()}
                  className="w-full text-xs bg-white/70 border border-violet-200/60 rounded-lg px-2.5 py-1.5 focus:outline-none text-slate-600 cursor-pointer font-mono mt-1"
                />
                <p className="text-[10px] text-slate-400 mt-1.5">
                  Configure este webhook no repositório do GitHub (como <span className="font-bold">application/json</span>) para registrar commits e automatizar tarefas.
                </p>
              </div>
            </div>

          </div>

          {/* Files Gallery */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100/80 pb-3 flex-wrap gap-2">
              <h2 className="text-lg font-bold text-slate-900">Arquivos do Projeto (Assets)</h2>
              
              <label className="btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-xl cursor-pointer hover:bg-slate-100 transition-colors">
                <UploadCloud className="w-4 h-4" />
                Upload Arquivo
                <input 
                  type="file" 
                  onChange={handleFileUpload} 
                  className="hidden" 
                  disabled={uploading} 
                />
              </label>
            </div>

            {uploadError && <p className="text-xs text-rose-500 font-semibold">{uploadError}</p>}
            
            {uploading && (
              <div className="flex items-center gap-2 text-violet-600 text-xs font-medium py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Fazendo upload do arquivo...
              </div>
            )}

            {assets.length === 0 ? (
              <div className="text-center py-8">
                <UploadCloud className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-xs text-slate-400 italic">Nenhum arquivo enviado para este projeto.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {assets.map(asset => {
                  const absoluteUrl = `${API_BASE_URL}/${asset.file_path}`;
                  return (
                    <div key={asset.id} className="p-3 bg-white border border-violet-100/40 rounded-xl flex items-center gap-3 group relative hover:border-violet-300 transition-all">
                      <div className="p-2 bg-slate-50 rounded-lg group-hover:bg-violet-50 transition-colors">
                        {getFileIcon(asset.file_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-slate-800 truncate" title={asset.file_name}>
                          {asset.file_name}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5">{formatBytes(asset.file_size)}</p>
                      </div>
                      <a 
                        href={absoluteUrl} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-800 transition-colors cursor-pointer"
                        title="Download"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right column: Tasks & Webhook Logs */}
        <div className="space-y-6">
          
          {/* Progress & Tasks Card */}
          <div className="glass-card p-6 space-y-6">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-violet-600" />
              Checklist de Tarefas
            </h2>
            
            <ProgressBar progress={progress} />

            <div className="border-t border-slate-100/80 pt-4">
              <TaskChecklist 
                projectId={id || ''} 
                admin={true} 
                onTasksUpdated={loadProjectData} 
              />
            </div>
          </div>

          {/* Webhooks logs card */}
          <div className="glass-card p-6 space-y-6">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-5 h-5 text-violet-600" />
              Logs de Integração
            </h2>

            {/* Commits List */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <GithubIcon className="w-3.5 h-3.5" />
                Commits GitHub
              </h3>

              {commits.length === 0 ? (
                <p className="text-xs text-slate-400 italic">Nenhum commit registrado ainda.</p>
              ) : (
                <ul className="space-y-2.5 max-h-[180px] overflow-y-auto pr-1">
                  {commits.map(c => (
                    <li key={c.id} className="p-2.5 bg-slate-50/50 border border-slate-100 rounded-lg text-xs">
                      <div className="flex justify-between font-semibold text-slate-700">
                        <span className="truncate max-w-[120px]">{c.author}</span>
                        <span className="text-slate-400 font-mono text-[10px]">{c.commit_hash.substring(0, 7)}</span>
                      </div>
                      <p className="text-slate-600 mt-1 break-words font-medium">{c.message}</p>
                      <span className="text-[9px] text-slate-400 block mt-0.5">
                        {new Date(c.commit_date).toLocaleString()}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Deploys List */}
            <div className="space-y-3 border-t border-slate-100/80 pt-4">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5" />
                Deploys Vercel/Netlify
              </h3>

              {deploys.length === 0 ? (
                <p className="text-xs text-slate-400 italic">Nenhum deploy registrado ainda.</p>
              ) : (
                <ul className="space-y-2.5 max-h-[180px] overflow-y-auto pr-1">
                  {deploys.map(d => (
                    <li key={d.id} className="p-2.5 bg-slate-50/50 border border-slate-100 rounded-lg text-xs flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-slate-700 uppercase">{d.provider}</span>
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                            d.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                          }`}>
                            {d.status}
                          </span>
                        </div>
                        {d.deploy_url && (
                          <a href={d.deploy_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-violet-600 font-medium hover:underline block truncate mt-0.5">
                            {d.deploy_url}
                          </a>
                        )}
                      </div>
                      <span className="text-[9px] text-slate-400 shrink-0 text-right">
                        {new Date(d.deploy_date).toLocaleDateString()}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

          </div>

        </div>

      </div>

      {/* Edit Form Modal */}
      {editOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-[fade-in_0.2s_ease-out]">
          <div className="bg-white rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl border border-slate-100 flex flex-col max-h-[90vh] animate-[scale-up_0.25s_cubic-bezier(0.34,1.56,0.64,1)]">
            
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Editar Detalhes do Projeto</h3>
                <p className="text-xs text-slate-500 mt-0.5">Atualize as informações operacionais do projeto.</p>
              </div>
              <button 
                onClick={() => setEditOpen(false)}
                className="p-1.5 rounded-xl hover:bg-slate-200/50 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleUpdateSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Nome do Projeto *</label>
                  <input
                    type="text"
                    name="name"
                    required
                    value={editForm.name}
                    onChange={handleEditChange}
                    className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>
                
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Nome do Cliente *</label>
                  <input
                    type="text"
                    name="client_name"
                    required
                    value={editForm.client_name}
                    onChange={handleEditChange}
                    className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Tipo de Projeto</label>
                  <select
                    name="project_type"
                    value={editForm.project_type}
                    onChange={handleEditChange}
                    className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  >
                    <option value="Landing Page">Landing Page</option>
                    <option value="Automação">Automação</option>
                    <option value="Web App">Web App</option>
                    <option value="Design/Figma">Design/Figma</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Valor (R$) *</label>
                  <input
                    type="number"
                    name="value"
                    required
                    value={editForm.value}
                    onChange={handleEditChange}
                    className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Status</label>
                  <select
                    name="status"
                    value={editForm.status}
                    onChange={handleEditChange}
                    className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  >
                    <option value="NEW">NEW</option>
                    <option value="IN_PROGRESS">IN PROGRESS</option>
                    <option value="REVIEW">REVIEW</option>
                    <option value="DEPLOYED">DEPLOYED</option>
                    <option value="DELIVERED">DELIVERED</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Descrição</label>
                <textarea
                  name="description"
                  rows={3}
                  value={editForm.description}
                  onChange={handleEditChange}
                  className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                    <GithubIcon className="w-3.5 h-3.5 text-slate-400" />
                    GitHub URL
                  </label>
                  <input
                    type="text"
                    name="github_url"
                    value={editForm.github_url}
                    onChange={handleEditChange}
                    className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-slate-400" />
                    Deploy URL
                  </label>
                  <input
                    type="text"
                    name="deploy_url"
                    value={editForm.deploy_url}
                    onChange={handleEditChange}
                    className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
                  />
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditOpen(false)}
                  className="btn-secondary px-5 py-2 rounded-xl text-sm cursor-pointer"
                  disabled={updating}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary px-5 py-2 rounded-xl text-sm flex items-center gap-2 cursor-pointer"
                  disabled={updating}
                >
                  {updating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Salvando...
                    </>
                  ) : (
                    'Salvar Alterações'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
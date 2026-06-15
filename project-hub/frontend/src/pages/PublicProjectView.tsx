import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPublicProject, API_BASE } from '../services/api';
import ProgressBar from '../components/ProgressBar';
import { 
  ShieldCheck, 
  Globe, 
  CheckCircle2, 
  Circle, 
  Loader2, 
  ExternalLink,
  Layers,
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

export default function PublicProjectView() {
  const { public_token } = useParams<{ public_token: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadPublicData = useCallback(async (silent = false) => {
    if (!public_token) return;
    try {
      if (!silent) setLoading(true);
      const result = await fetchPublicProject(public_token);
      setData(result);
      setError('');
    } catch (err: any) {
      console.error(err);
      setError('Projeto não encontrado ou token inválido.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [public_token]);

  useEffect(() => {
    loadPublicData();
  }, [loadPublicData]);

  useEffect(() => {
    if (!public_token) return;

    const eventSource = new EventSource(`${API_BASE}/webhooks/events/${public_token}`);
    eventSource.onmessage = (event) => {
      if (event.data === 'reload') {
        loadPublicData(true);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [public_token, loadPublicData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <Loader2 className="w-10 h-10 text-violet-600 animate-spin" />
        <p className="text-slate-500 font-medium">Carregando portal do cliente...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-md mx-auto mt-16 p-8 text-center glass-card border-rose-100/50">
        <Layers className="w-12 h-12 text-rose-300 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-slate-800">Acesso Não Autorizado</h3>
        <p className="text-sm text-slate-500 mt-2">{error || 'Token inválido.'}</p>
      </div>
    );
  }

  const { project, tasks, commits, deploys, progress } = data;

  const statusLabels: any = {
    NEW: 'Novo',
    IN_PROGRESS: 'Em Desenvolvimento',
    REVIEW: 'Em Revisão',
    DEPLOYED: 'Publicado (Deploy)',
    DELIVERED: 'Entregue'
  };

  const statusColors: any = {
    NEW: 'bg-blue-50 text-blue-700 border-blue-200/50',
    IN_PROGRESS: 'bg-violet-50 text-violet-700 border-violet-200/50',
    REVIEW: 'bg-amber-50 text-amber-800 border-amber-200/50',
    DEPLOYED: 'bg-emerald-50 text-emerald-800 border-emerald-200/50',
    DELIVERED: 'bg-emerald-100 text-emerald-900 border-emerald-300/50'
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-8 space-y-8 animate-[fade-in_0.3s_ease-out]">
      
      {/* Decorative Brand Header */}
      <div className="text-center space-y-2 pb-2">
        <div className="inline-flex items-center gap-1 bg-violet-100/80 border border-violet-200/30 text-violet-800 text-xs font-bold px-3 py-1 rounded-full">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          Portal de Acompanhamento Dominuslabs
        </div>
        <p className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Ambiente Seguro do Cliente</p>
      </div>

      {/* Main Glassmorphic Panel */}
      <div className="glass-card overflow-hidden">
        
        {/* Panel Header */}
        <div className="p-6 sm:p-8 border-b border-violet-100/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/40">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900">{project.name}</h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1 font-medium">
              Cliente: <span className="text-slate-800 font-semibold">{project.client_name}</span>
            </p>
          </div>
          
          <div className="flex items-center gap-2.5">
            <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Status:</span>
            <span className={`text-xs font-bold px-3 py-1 rounded-full border ${statusColors[project.status] || 'bg-slate-100 text-slate-700'}`}>
              {statusLabels[project.status] || project.status}
            </span>
          </div>
        </div>

        {/* Body content */}
        <div className="p-6 sm:p-8 space-y-8">
          
          {/* Progress bar container */}
          <div className="p-5 bg-slate-50/50 border border-slate-100 rounded-2xl">
            <ProgressBar progress={progress} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Checklist Column */}
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-violet-600" />
                Status das Atividades
              </h2>
              
              {tasks.length === 0 ? (
                <p className="text-xs text-slate-400 italic">Nenhuma atividade registrada.</p>
              ) : (
                <ul className="space-y-3">
                  {tasks.map((task: any) => {
                    const isDone = task.status === 'DONE';
                    return (
                      <li 
                        key={task.id} 
                        className={`flex items-start gap-3 p-3.5 border rounded-2xl transition-colors ${
                          isDone 
                            ? 'bg-slate-50/70 border-slate-200/40 text-slate-400' 
                            : 'bg-white border-violet-100/50 text-slate-700 shadow-sm'
                        }`}
                      >
                        <div className="mt-0.5 shrink-0">
                          {isDone ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-500 fill-emerald-50" />
                          ) : (
                            <Circle className="w-5 h-5 text-slate-300" />
                          )}
                        </div>
                        <span className={`text-sm font-semibold leading-tight break-words ${isDone ? 'line-through' : ''}`}>
                          {task.name}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            {/* History logs Column */}
            <div className="space-y-6">
              
              {/* Commits */}
              <div className="space-y-3">
                <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <GithubIcon className="w-4 h-4" />
                  Atualizações de Código
                </h2>

                {commits.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">Nenhuma atualização registrada ainda.</p>
                ) : (
                  <ul className="space-y-2.5 max-h-[160px] overflow-y-auto pr-1">
                    {commits.map((c: any) => (
                      <li key={c.id} className="p-3 bg-white/70 border border-slate-100/60 rounded-xl text-xs space-y-1">
                        <div className="flex justify-between text-slate-400 font-semibold text-[10px]">
                          <span>{c.author}</span>
                          <span className="font-mono">{c.commit_hash.substring(0, 7)}</span>
                        </div>
                        <p className="text-slate-700 font-medium break-words">{c.message}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Deploys */}
              <div className="space-y-3">
                <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  Deploys do Sistema
                </h2>

                {deploys.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">Nenhum deploy realizado.</p>
                ) : (
                  <ul className="space-y-2.5 max-h-[160px] overflow-y-auto pr-1">
                    {deploys.map((d: any) => (
                      <li key={d.id} className="p-3 bg-white/70 border border-slate-100/60 rounded-xl text-xs flex items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-700 uppercase">{d.provider}</span>
                            <span className="bg-emerald-50 text-emerald-700 font-bold px-1.5 py-0.5 rounded text-[9px] border border-emerald-100">
                              {d.status}
                            </span>
                          </div>
                          {d.deploy_url && (
                            <span className="text-[10px] text-slate-400 block truncate mt-0.5 max-w-[220px]">
                              {d.deploy_url}
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-400 shrink-0 font-medium">
                          {new Date(d.deploy_date).toLocaleDateString()}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Preview Button */}
              {project.deploy_url && (
                <div className="pt-4 border-t border-slate-100/80">
                  <a
                    href={project.deploy_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary w-full flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-bold shadow-md cursor-pointer hover:scale-[1.01] active:scale-[0.99] transition-all"
                  >
                    Visualizar Preview da Página
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              )}

            </div>

          </div>

        </div>

      </div>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
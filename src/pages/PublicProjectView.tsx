import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPublicProject, API_BASE, submitFeedback } from '../services/api';
import ProgressBar from '../components/ProgressBar';
import Footer from '../components/Footer';
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

  // Feedback Form State
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);
  const [feedbackError, setFeedbackError] = useState('');
  const [rating, setRating] = useState(5);
  const [formFields, setFormFields] = useState({
    final_result: '',
    service_rating: '',
    invested_value_rating: '',
    process_rating: '',
    improvements: ''
  });

  const handleFieldChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormFields(prev => ({ ...prev, [name]: value }));
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!public_token) return;

    try {
      setSubmittingFeedback(true);
      setFeedbackError('');
      await submitFeedback({
        project_token: public_token,
        rating,
        ...formFields
      });
      setFeedbackSuccess(true);
      loadPublicData(true);
    } catch (err: any) {
      console.error(err);
      setFeedbackError('Erro ao enviar avaliação.');
    } finally {
      setSubmittingFeedback(false);
    }
  };

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
        <Loader2 className="w-10 h-10 text-purple-600 animate-spin" />
        <p className="text-zinc-500 font-medium">Carregando portal do cliente...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-md mx-auto mt-16 p-8 text-center surface-card border-rose-100/50">
        <Layers className="w-12 h-12 text-rose-300 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-zinc-800">Acesso Não Autorizado</h3>
        <p className="text-sm text-zinc-500 mt-2">{error || 'Token inválido.'}</p>
      </div>
    );
  }

  const { project, tasks, commits, deploys, progress, feedback_submitted } = data;

  const statusLabels: any = {
    NEW: 'Novo',
    IN_PROGRESS: 'Em Desenvolvimento',
    REVIEW: 'Em Revisão',
    DEPLOYED: 'Publicado (Deploy)',
    DELIVERED: 'Entregue'
  };

  const statusColors: any = {
    NEW: 'bg-blue-50 text-blue-700 border-blue-200/50',
    IN_PROGRESS: 'bg-purple-50 text-purple-700 border-purple-200/50',
    REVIEW: 'bg-amber-50 text-amber-800 border-amber-200/50',
    DEPLOYED: 'bg-emerald-50 text-emerald-800 border-emerald-200/50',
    DELIVERED: 'bg-emerald-100 text-emerald-900 border-emerald-300/50'
  };

  return (
    <div className="min-h-screen  relative overflow-hidden flex flex-col justify-between">
      {/* Background Animation Bubbles */}
      <div className="animated-bg">
        <div className="bg-bubble-1"></div>
        <div className="bg-bubble-2"></div>
        <div className="bg-bubble-3"></div>
      </div>

      <div className="max-w-4xl mx-auto w-full p-4 sm:p-8 space-y-8 animate-[fade-in_0.3s_ease-out] flex-1">
      
      {/* Decorative Brand Header */}
      <div className="text-center space-y-2 pb-2">
        <div className="inline-flex items-center gap-1 bg-purple-100/80 border border-purple-200/30 text-purple-800 text-xs font-bold px-3 py-1 rounded-full">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          Portal de Acompanhamento Dominuslabs
        </div>
        <p className="text-xs text-zinc-400 font-semibold tracking-wider uppercase">Ambiente Seguro do Cliente</p>
      </div>

      {/* Main Glassmorphic Panel */}
      <div className="surface-card overflow-hidden">
        
        {/* Panel Header */}
        <div className="p-6 sm:p-8 border-b border-zinc-200/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-zinc-900">{project.name}</h1>
            <p className="text-xs sm:text-sm text-zinc-500 mt-1 font-medium">
              Cliente: <span className="text-zinc-800 font-semibold">{project.client_name}</span>
            </p>
          </div>
          
          <div className="flex items-center gap-2.5">
            <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider">Status:</span>
            <span className={`text-xs font-bold px-3 py-1 rounded-full border ${statusColors[project.status] || 'bg-zinc-100 text-zinc-700'}`}>
              {statusLabels[project.status] || project.status}
            </span>
          </div>
        </div>

        {/* Body content */}
        <div className="p-6 sm:p-8 space-y-8">
          
          {/* Progress bar container */}
          <div className="p-5  border border-zinc-100 rounded-2xl">
            <ProgressBar progress={progress} />
          </div>

          {/* Client Feedback Section */}
          {project.status === 'DELIVERED' && (
            <div className="p-6 bg-gradient-to-br from-purple-50/50 to-indigo-50/50 border border-zinc-200 rounded-3xl space-y-6">
              {(feedback_submitted || feedbackSuccess) ? (
                <div className="text-center py-6 space-y-3">
                  <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-bold text-zinc-800">Avaliação Enviada!</h3>
                  <p className="text-sm text-zinc-500 max-w-md mx-auto">
                    Agradecemos imensamente pelo seu feedback! Ele nos ajuda a aprimorar nossos processos e a entregar soluções cada vez melhores na Dominuslabs.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleFeedbackSubmit} className="space-y-5">
                  <div className="border-b border-zinc-200 pb-3">
                    <h3 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-amber-500 animate-pulse" />
                      Avalie o Nosso Serviço
                    </h3>
                    <p className="text-xs text-zinc-500 mt-1">
                      Seu projeto foi concluído! Por favor, responda este rápido formulário para avaliá-lo.
                    </p>
                  </div>

                  {feedbackError && (
                    <div className="p-3 bg-rose-50 border border-rose-100 rounded-xl text-rose-700 text-xs font-semibold text-center">
                      {feedbackError}
                    </div>
                  )}

                  {/* Rating Selector */}
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider block">Nota Geral *</label>
                    <div className="flex items-center gap-1.5">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setRating(star)}
                          className="p-1 hover:scale-110 transition-transform cursor-pointer"
                        >
                          <svg
                            className={`w-8 h-8 ${star <= rating ? 'text-amber-400 fill-amber-400' : 'text-zinc-300'}`}
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Open-ended Questions */}
                  <div className="space-y-4">
                    <div className="space-y-1">
                      <label className="text-xs font-bold text-zinc-600">O que você achou do resultado final do projeto? *</label>
                      <textarea
                        name="final_result"
                        required
                        rows={2}
                        value={formFields.final_result}
                        onChange={handleFieldChange}
                        placeholder="Ex: Excelente, superou minhas expectativas..."
                        className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500  resize-none"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-bold text-zinc-600">O que achou do nosso atendimento? *</label>
                      <textarea
                        name="service_rating"
                        required
                        rows={2}
                        value={formFields.service_rating}
                        onChange={handleFieldChange}
                        placeholder="Ex: Muito atenciosos e ágeis no suporte..."
                        className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500  resize-none"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-bold text-zinc-600">O que achou do valor investido? *</label>
                      <textarea
                        name="invested_value_rating"
                        required
                        rows={2}
                        value={formFields.invested_value_rating}
                        onChange={handleFieldChange}
                        placeholder="Ex: Excelente custo-benefício, valeu cada centavo..."
                        className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500  resize-none"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-bold text-zinc-600">Como avalia o processo do início ao fim do desenvolvimento? *</label>
                      <textarea
                        name="process_rating"
                        required
                        rows={2}
                        value={formFields.process_rating}
                        onChange={handleFieldChange}
                        placeholder="Ex: Transparente, com acompanhamento em tempo real..."
                        className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500  resize-none"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-bold text-zinc-600">O que poderíamos melhorar no projeto e, no geral, na Dominuslabs? *</label>
                      <textarea
                        name="improvements"
                        required
                        rows={2}
                        value={formFields.improvements}
                        onChange={handleFieldChange}
                        placeholder="Escreva sugestões de melhoria ou pontos a aprimorar..."
                        className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500  resize-none"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={submittingFeedback}
                    className="btn-primary w-full flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-bold shadow-md cursor-pointer disabled:opacity-50 transition-all"
                  >
                    {submittingFeedback ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Enviando avaliação...
                      </>
                    ) : (
                      'Enviar Avaliação'
                    )}
                  </button>
                </form>
              )}
            </div>
          ) }

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Checklist Column */}
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-purple-600" />
                Status das Atividades
              </h2>
              
              {tasks.length === 0 ? (
                <p className="text-xs text-zinc-400 italic">Nenhuma atividade registrada.</p>
              ) : (
                <ul className="space-y-3">
                  {tasks.map((task: any) => {
                    const isDone = task.status === 'DONE';
                    return (
                      <li 
                        key={task.id} 
                        className={`flex items-start gap-3 p-3.5 border rounded-2xl transition-colors ${
                          isDone 
                            ? ' border-zinc-200/40 text-zinc-400' 
                            : 'bg-white border-zinc-200/50 text-zinc-700 shadow-sm'
                        }`}
                      >
                        <div className="mt-0.5 shrink-0">
                          {isDone ? (
                            <CheckCircle2 className="w-5 h-5 text-emerald-500 fill-emerald-50" />
                          ) : (
                            <Circle className="w-5 h-5 text-zinc-300" />
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
                <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                  <GithubIcon className="w-4 h-4" />
                  Atualizações de Código
                </h2>

                {commits.length === 0 ? (
                  <p className="text-xs text-zinc-400 italic">Nenhuma atualização registrada ainda.</p>
                ) : (
                  <ul className="space-y-2.5 max-h-[160px] overflow-y-auto pr-1">
                    {commits.map((c: any) => (
                      <li key={c.id} className="p-3  border border-zinc-100/60 rounded-xl text-xs space-y-1">
                        <div className="flex justify-between text-zinc-400 font-semibold text-[10px]">
                          <span>{c.author}</span>
                          <span className="font-mono">{c.commit_hash.substring(0, 7)}</span>
                        </div>
                        <p className="text-zinc-700 font-medium break-words">{c.message}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Deploys */}
              <div className="space-y-3">
                <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  Deploys do Sistema
                </h2>

                {deploys.length === 0 ? (
                  <p className="text-xs text-zinc-400 italic">Nenhum deploy realizado.</p>
                ) : (
                  <ul className="space-y-2.5 max-h-[160px] overflow-y-auto pr-1">
                    {deploys.map((d: any) => (
                      <li key={d.id} className="p-3  border border-zinc-100/60 rounded-xl text-xs flex items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-zinc-700 uppercase">{d.provider}</span>
                            <span className="bg-emerald-50 text-emerald-700 font-bold px-1.5 py-0.5 rounded text-[9px] border border-emerald-100">
                              {d.status}
                            </span>
                          </div>
                          {d.deploy_url && (
                            <span className="text-[10px] text-zinc-400 block truncate mt-0.5 max-w-[220px]">
                              {d.deploy_url}
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-zinc-400 shrink-0 font-medium">
                          {new Date(d.deploy_date).toLocaleDateString()}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Preview Button */}
              {project.deploy_url && (
                <div className="pt-4 border-t border-zinc-100/80">
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

      </div>

      <Footer />

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
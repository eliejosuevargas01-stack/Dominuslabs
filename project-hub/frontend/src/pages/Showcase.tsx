import { useState, useEffect } from 'react';
import { fetchShowcaseData, API_BASE } from '../services/api';
import Footer from '../components/Footer';
import { 
  FolderCheck, 
  Clock, 
  Star, 
  MessageSquare, 
  Sparkles, 
  Loader2, 
  ArrowRight,
  TrendingUp,
  Award,
  Play,
  Video,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  X,
  ExternalLink
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Showcase({ isDashboard = false }: { isDashboard?: boolean }) {
  const [data, setData] = useState<{ projects: any[]; testimonials: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'completed' | 'ongoing'>('completed');
  
  // Modal states for full case view
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  const [currentMediaIndex, setCurrentMediaIndex] = useState<number>(0);

  useEffect(() => {
    const loadShowcase = async () => {
      try {
        setLoading(true);
        const res = await fetchShowcaseData();
        setData(res);
        setError('');
      } catch (err: any) {
        console.error(err);
        setError('Não foi possível carregar os cases de sucesso.');
      } finally {
        setLoading(false);
      }
    };
    loadShowcase();
  }, []);

  // Keyboard navigation for Escape to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedProject(null);
      }
    };
    if (selectedProject) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedProject]);

  if (loading) {
    return (
      <div className={isDashboard ? "flex flex-col items-center justify-center min-h-[300px]" : "flex flex-col items-center justify-center min-h-screen gap-4 bg-slate-50 relative overflow-hidden"}>
        {/* Background Animation Bubbles */}
        {!isDashboard && (
          <div className="animated-bg">
            <div className="bg-bubble-1"></div>
            <div className="bg-bubble-2"></div>
          </div>
        )}
        <Loader2 className="w-10 h-10 text-violet-600 animate-spin z-10" />
        <p className="text-slate-500 font-medium z-10">Carregando cases de sucesso...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={isDashboard ? "flex flex-col items-center justify-center p-4" : "flex flex-col items-center justify-center min-h-screen p-4 bg-slate-50 relative overflow-hidden"}>
        <div className="max-w-md w-full text-center glass-card p-8 border-rose-100 z-10">
          <FolderCheck className="w-12 h-12 text-rose-400 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-800">Ops! Algo deu errado</h3>
          <p className="text-sm text-slate-500 mt-2">{error || 'Erro ao carregar dados.'}</p>
        </div>
      </div>
    );
  }

  // Filter projects by status
  const completedProjects = data.projects.filter(
    (p) => p.status === 'DELIVERED' || p.status === 'DEPLOYED'
  );
  
  const ongoingProjects = data.projects.filter(
    (p) => p.status === 'NEW' || p.status === 'IN_PROGRESS' || p.status === 'REVIEW'
  );

  // Find matching client testimonial
  const projectTestimonial = selectedProject
    ? data.testimonials.find((t) => t.project_name === selectedProject.name)
    : null;

  // Carrousel navigations
  const nextMedia = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectedProject?.assets) return;
    setCurrentMediaIndex((prev) => (prev + 1) % selectedProject.assets.length);
  };

  const prevMedia = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectedProject?.assets) return;
    setCurrentMediaIndex((prev) => (prev - 1 + selectedProject.assets.length) % selectedProject.assets.length);
  };

  return (
    <div className={isDashboard ? "relative z-10 w-full" : "min-h-screen bg-slate-50/50 relative overflow-hidden flex flex-col justify-between"}>
      {/* Background Animation Bubbles */}
      {!isDashboard && (
        <div className="animated-bg">
          <div className="bg-bubble-1"></div>
          <div className="bg-bubble-2"></div>
          <div className="bg-bubble-3"></div>
        </div>
      )}

      <div className={isDashboard ? "w-full space-y-6" : "max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-8 relative z-10 flex-1"}>
        
        {/* Navigation / Brand Header */}
        {!isDashboard && (
          <header className="flex items-center justify-between pb-12">
            <Link to="/" className="flex items-center gap-2 group">
              <img src="/logo.png" alt="Dominus Labs" className="w-9 h-9 rounded-xl object-contain shadow-md group-hover:scale-105 transition-transform" />
              <span className="font-display font-extrabold text-2xl tracking-tight bg-gradient-to-r from-violet-800 via-indigo-700 to-emerald-600 bg-clip-text text-transparent">
                Dominuslabs
              </span>
            </Link>
            <span className="text-xs font-semibold px-3 py-1 rounded-full bg-violet-100/70 text-violet-800 border border-violet-200/40">
              Cases de Sucesso
            </span>
          </header>
        )}

        {/* Hero Section */}
        <section className="text-center max-w-3xl mx-auto space-y-4 pb-16">
          <div className="inline-flex items-center gap-1.5 bg-amber-100 text-amber-800 border border-amber-200/50 text-[10px] font-extrabold uppercase tracking-wider px-3.5 py-1 rounded-full shadow-sm">
            <Award className="w-3.5 h-3.5" />
            Portfólio & Depoimentos
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Nossos Projetos e <span className="bg-gradient-to-r from-violet-700 to-indigo-600 bg-clip-text text-transparent">Cases de Sucesso</span>
          </h1>
          <p className="text-slate-500 text-base sm:text-lg max-w-2xl mx-auto font-medium">
            Explore os projetos que desenvolvemos e veja a avaliação sincera de nossos clientes reais sobre o resultado final, atendimento e processo de entrega.
          </p>
        </section>

        {/* Showcase Grid Section */}
        <section className="space-y-8">
          
          {/* Tabs header */}
          <div className="flex justify-center">
            <div className="bg-slate-100 p-1.5 rounded-2xl flex gap-1 shadow-inner border border-slate-200/40">
              <button
                onClick={() => setActiveTab('completed')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer ${
                  activeTab === 'completed'
                    ? 'bg-white text-violet-700 shadow-md'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <FolderCheck className="w-4 h-4" />
                Concluídos ({completedProjects.length})
              </button>
              <button
                onClick={() => setActiveTab('ongoing')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer ${
                  activeTab === 'ongoing'
                    ? 'bg-white text-violet-700 shadow-md'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Clock className="w-4 h-4" />
                Em Desenvolvimento ({ongoingProjects.length})
              </button>
            </div>
          </div>

          {/* Tab Content: Completed Projects */}
          {activeTab === 'completed' ? (
            completedProjects.length === 0 ? (
              <div className="text-center py-12 glass-card max-w-md mx-auto">
                <FolderCheck className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-xs text-slate-400 italic">Nenhum projeto concluído no momento.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {completedProjects.map((proj, idx) => {
                  const media = proj.assets || [];
                  const imageAssets = media.filter((a: any) => a.file_type === 'images');
                  const videoAssets = media.filter((a: any) => a.file_type === 'videos');
                  const firstImage = imageAssets[0];
                  const firstVideo = videoAssets[0];
                  
                  const hasMedia = media.length > 0;
                  const coverUrl = firstImage 
                    ? `${API_BASE}/${firstImage.file_path}` 
                    : firstVideo 
                      ? `${API_BASE}/${firstVideo.file_path}` 
                      : null;
                  const isVideo = !firstImage && firstVideo;

                  return (
                    <div key={idx} className="glass-card flex flex-col justify-between group hover:border-violet-300 hover:shadow-lg transition-all relative overflow-hidden h-[450px]">
                      {/* Media Header Preview */}
                      <div className="h-48 w-full relative overflow-hidden bg-slate-900 shrink-0">
                        {hasMedia ? (
                          isVideo ? (
                            <div className="w-full h-full relative">
                              <video src={coverUrl || undefined} muted className="w-full h-full object-cover opacity-85" />
                              <div className="absolute inset-0 bg-slate-950/40 flex items-center justify-center group-hover:bg-slate-950/20 transition-all">
                                <Play className="w-9 h-9 text-white fill-white/80 drop-shadow-md" />
                              </div>
                              <span className="absolute top-3 left-3 text-[9px] font-bold px-2 py-0.5 rounded bg-violet-600 text-white flex items-center gap-1 uppercase tracking-wide">
                                <Video className="w-3 h-3" /> Vídeo
                              </span>
                            </div>
                          ) : (
                            <div className="w-full h-full relative">
                              <img src={coverUrl || undefined} alt={proj.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                              <div className="absolute inset-0 bg-slate-950/10 group-hover:bg-transparent transition-all"></div>
                              {media.length > 1 && (
                                <span className="absolute bottom-3 right-3 text-[9px] font-bold px-2.5 py-0.5 rounded bg-slate-950/60 backdrop-blur text-white uppercase tracking-wider">
                                  +{media.length - 1} Arquivos
                                </span>
                              )}
                            </div>
                          )
                        ) : (
                          // Premium default gradient preview if no assets
                          <div className="w-full h-full bg-gradient-to-br from-violet-600/15 via-indigo-600/10 to-emerald-500/10 flex items-center justify-center relative">
                            <div className="absolute -top-10 -left-10 w-24 h-24 bg-violet-500/10 rounded-full blur-xl"></div>
                            <div className="absolute -bottom-10 -right-10 w-24 h-24 bg-emerald-500/15 rounded-full blur-xl"></div>
                            <FolderCheck className="w-12 h-12 text-violet-500/30" />
                          </div>
                        )}
                        {/* Status Badge */}
                        <span className="absolute top-3 right-3 text-[9px] font-extrabold px-2.5 py-0.5 rounded bg-emerald-500 text-white uppercase tracking-wider">
                          Pronto
                        </span>
                      </div>

                      {/* Card Body */}
                      <div className="p-5 flex-1 flex flex-col justify-between">
                        <div className="space-y-2">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">
                            {proj.project_type}
                          </span>
                          <h3 className="text-base sm:text-lg font-bold text-slate-800 tracking-tight line-clamp-1 group-hover:text-violet-700 transition-colors">
                            {proj.name}
                          </h3>
                          <p className="text-slate-500 text-xs leading-relaxed line-clamp-3 font-medium">
                            {proj.description || 'Projeto concluído com sucesso e entregue de acordo com os requisitos do cliente.'}
                          </p>
                        </div>

                        <div className="space-y-3 mt-4">
                          <div className="pt-3 border-t border-slate-100/50 flex items-center justify-between text-xs text-slate-400 font-semibold">
                            <span>Dominuslabs Case</span>
                            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                          </div>
                          
                          <div className="flex gap-2">
                            <button 
                              onClick={() => { setSelectedProject(proj); setCurrentMediaIndex(0); }}
                              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl border border-violet-100 text-violet-700 bg-violet-50/50 hover:bg-violet-600 hover:text-white hover:border-violet-600 transition-all font-bold text-xs cursor-pointer shadow-sm"
                            >
                              <span>Ver Case Completo</span>
                              <Maximize2 className="w-3.5 h-3.5" />
                            </button>
                            {proj.deploy_url && (
                              <a 
                                href={proj.deploy_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-1 py-2.5 px-3 rounded-xl border border-emerald-100 bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white hover:border-emerald-600 transition-all font-bold text-xs cursor-pointer shadow-sm shrink-0"
                                title="Acessar Sistema Online"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )
          ) : (
            ongoingProjects.length === 0 ? (
              <div className="text-center py-12 glass-card max-w-md mx-auto">
                <Clock className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-xs text-slate-400 italic">Nenhum projeto em desenvolvimento no momento.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {ongoingProjects.map((proj, idx) => {
                  const media = proj.assets || [];
                  const imageAssets = media.filter((a: any) => a.file_type === 'images');
                  const videoAssets = media.filter((a: any) => a.file_type === 'videos');
                  const firstImage = imageAssets[0];
                  const firstVideo = videoAssets[0];
                  
                  const hasMedia = media.length > 0;
                  const coverUrl = firstImage 
                    ? `${API_BASE}/${firstImage.file_path}` 
                    : firstVideo 
                      ? `${API_BASE}/${firstVideo.file_path}` 
                      : null;
                  const isVideo = !firstImage && firstVideo;

                  return (
                    <div key={idx} className="glass-card flex flex-col justify-between group hover:border-violet-300 hover:shadow-lg transition-all relative overflow-hidden h-[450px]">
                      {/* Media Header Preview */}
                      <div className="h-48 w-full relative overflow-hidden bg-slate-900 shrink-0">
                        {hasMedia ? (
                          isVideo ? (
                            <div className="w-full h-full relative">
                              <video src={coverUrl || undefined} muted className="w-full h-full object-cover opacity-85" />
                              <div className="absolute inset-0 bg-slate-950/40 flex items-center justify-center group-hover:bg-slate-950/20 transition-all">
                                <Play className="w-9 h-9 text-white fill-white/80 drop-shadow-md" />
                              </div>
                              <span className="absolute top-3 left-3 text-[9px] font-bold px-2 py-0.5 rounded bg-violet-600 text-white flex items-center gap-1 uppercase tracking-wide">
                                <Video className="w-3 h-3" /> Vídeo
                              </span>
                            </div>
                          ) : (
                            <div className="w-full h-full relative">
                              <img src={coverUrl || undefined} alt={proj.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                              <div className="absolute inset-0 bg-slate-950/10 group-hover:bg-transparent transition-all"></div>
                              {media.length > 1 && (
                                <span className="absolute bottom-3 right-3 text-[9px] font-bold px-2.5 py-0.5 rounded bg-slate-950/60 backdrop-blur text-white uppercase tracking-wider">
                                  +{media.length - 1} Arquivos
                                </span>
                              )}
                            </div>
                          )
                        ) : (
                          // Premium default gradient preview if no assets
                          <div className="w-full h-full bg-gradient-to-br from-violet-600/15 via-indigo-600/10 to-emerald-500/10 flex items-center justify-center relative">
                            <div className="absolute -top-10 -left-10 w-24 h-24 bg-violet-500/10 rounded-full blur-xl"></div>
                            <div className="absolute -bottom-10 -right-10 w-24 h-24 bg-emerald-500/15 rounded-full blur-xl"></div>
                            <FolderCheck className="w-12 h-12 text-violet-500/30" />
                          </div>
                        )}
                        {/* Status Badge */}
                        <span className="absolute top-3 right-3 text-[9px] font-extrabold px-2.5 py-0.5 rounded bg-violet-500 text-white uppercase tracking-wider">
                          Em Progresso
                        </span>
                      </div>

                      {/* Card Body */}
                      <div className="p-5 flex-1 flex flex-col justify-between">
                        <div className="space-y-2">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">
                            {proj.project_type}
                          </span>
                          <h3 className="text-base sm:text-lg font-bold text-slate-800 tracking-tight line-clamp-1 group-hover:text-violet-700 transition-colors">
                            {proj.name}
                          </h3>
                          <p className="text-slate-500 text-xs leading-relaxed line-clamp-3 font-medium">
                            {proj.description || 'Desenvolvimento ativo. Siga os detalhes e deploys de homologação em tempo real.'}
                          </p>
                        </div>

                        <div className="space-y-3 mt-4">
                          <div className="pt-3 border-t border-slate-100/50 flex items-center justify-between text-xs text-slate-400 font-semibold">
                            <span>Desenvolvimento Ativo</span>
                            <TrendingUp className="w-3.5 h-3.5 text-violet-500" />
                          </div>
                          
                          <div className="flex gap-2">
                            <button 
                              onClick={() => { setSelectedProject(proj); setCurrentMediaIndex(0); }}
                              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl border border-violet-100 text-violet-700 bg-violet-50/50 hover:bg-violet-600 hover:text-white hover:border-violet-600 transition-all font-bold text-xs cursor-pointer shadow-sm"
                            >
                              <span>Ver Detalhes do Projeto</span>
                              <Maximize2 className="w-3.5 h-3.5" />
                            </button>
                            {proj.deploy_url && (
                              <a 
                                href={proj.deploy_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-1 py-2.5 px-3 rounded-xl border border-emerald-100 bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white hover:border-emerald-600 transition-all font-bold text-xs cursor-pointer shadow-sm shrink-0"
                                title="Acessar Sistema Online"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )
          )}
        </section>

        {/* Testimonials Section */}
        <section className="pt-24 space-y-10">
          <div className="text-center max-w-md mx-auto space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 flex items-center justify-center gap-2">
              <MessageSquare className="w-6 h-6 text-violet-600" />
              O Que Dizem Nossos Clientes
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 font-medium">
              Avaliações reais colhidas diretamente do painel seguro após a conclusão do projeto.
            </p>
          </div>

          {data.testimonials.length === 0 ? (
            <div className="text-center py-12 glass-card max-w-md mx-auto">
              <Star className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-xs text-slate-400 italic">Nenhum depoimento publicado ainda.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {data.testimonials.map((test, idx) => (
                <div key={idx} className="glass-card p-6 sm:p-8 space-y-6 flex flex-col justify-between hover:border-violet-200 hover:shadow-md transition-all relative">
                  
                  {/* Testimonial Header / Stars */}
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star 
                          key={star} 
                          className={`w-4 h-4 ${star <= test.rating ? 'text-amber-400 fill-amber-400' : 'text-slate-300'}`} 
                        />
                      ))}
                    </div>
                    <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-100 uppercase tracking-wider">
                      {test.project_type}
                    </span>
                  </div>

                  {/* Comment */}
                  <blockquote className="text-sm sm:text-base text-slate-600 font-medium italic leading-relaxed break-words flex-1 py-2">
                    "{test.comment}"
                  </blockquote>

                  {/* Client Metadata */}
                  <div className="border-t border-slate-100/80 pt-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 text-white flex items-center justify-center font-bold text-sm">
                      {test.client_name.charAt(0)}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-800 leading-tight">{test.client_name}</h4>
                      <p className="text-[10px] text-slate-400 font-semibold mt-0.5">Projeto: {test.project_name}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Dynamic CTA Footer Section */}
        {!isDashboard && (
          <section className="pt-24 text-center">
            <div className="glass-card p-8 sm:p-12 max-w-4xl mx-auto bg-gradient-to-br from-violet-700 to-indigo-900 text-white border-violet-600/30 flex flex-col items-center space-y-6 shadow-xl relative overflow-hidden">
              <div className="absolute -top-10 -left-10 w-40 h-40 bg-white/5 rounded-full blur-xl"></div>
              <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-emerald-500/10 rounded-full blur-xl"></div>

              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Quer automatizar e escalar seu negócio?</h2>
              <p className="text-violet-200 text-sm sm:text-base max-w-xl font-medium">
                Entre em contato conosco hoje mesmo para desenharmos juntos a solução perfeita de landing pages, integrações, CRMs ou automações.
              </p>
              <a
                href="https://wa.me/5500000000000"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-white text-violet-800 hover:bg-violet-50 px-6 py-3 rounded-2xl font-extrabold text-sm shadow-md transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
              >
                Falar com Eliezer
                <ArrowRight className="w-4 h-4 text-violet-800" />
              </a>
            </div>
          </section>
        )}

      </div>

      {/* Detailed Case Modal */}
      {selectedProject && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md animate-[fade-in_0.2s_ease-out]"
          onClick={() => setSelectedProject(null)}
        >
          <div 
            className="bg-white rounded-3xl w-full max-w-4xl overflow-hidden shadow-2xl border border-slate-100 flex flex-col md:flex-row max-h-[90vh] md:max-h-[80vh] animate-[scale-up_0.25s_cubic-bezier(0.34,1.56,0.64,1)]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Left Media Carrousel */}
            <div className="w-full md:w-1/2 bg-slate-950 flex flex-col justify-between relative overflow-hidden h-[300px] md:h-auto min-h-[300px]">
              {selectedProject.assets && selectedProject.assets.length > 0 ? (
                <>
                  {/* Media Content */}
                  <div className="flex-1 flex items-center justify-center relative group/media w-full h-full">
                    {selectedProject.assets[currentMediaIndex].file_type === 'videos' ? (
                      <video 
                        key={selectedProject.assets[currentMediaIndex].id}
                        src={`${API_BASE}/${selectedProject.assets[currentMediaIndex].file_path}`} 
                        controls 
                        autoPlay
                        className="w-full h-full object-contain" 
                      />
                    ) : (
                      <div className="w-full h-full relative">
                        {/* Blurred background image for elegant preview aspect ratio */}
                        <div 
                          className="absolute inset-0 bg-cover bg-center blur-2xl opacity-30 scale-110"
                          style={{ backgroundImage: `url(${API_BASE}/${selectedProject.assets[currentMediaIndex].file_path})` }}
                        ></div>
                        <img 
                          src={`${API_BASE}/${selectedProject.assets[currentMediaIndex].file_path}`} 
                          alt={selectedProject.name} 
                          className="w-full h-full object-contain relative z-10" 
                        />
                      </div>
                    )}

                    {/* Chevron Controls (only if more than 1 asset) */}
                    {selectedProject.assets.length > 1 && (
                      <>
                        <button 
                          onClick={prevMedia}
                          className="absolute left-4 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 hover:bg-black/80 text-white z-20 cursor-pointer transition-all hover:scale-105 border border-white/10"
                        >
                          <ChevronLeft className="w-5 h-5" />
                        </button>
                        <button 
                          onClick={nextMedia}
                          className="absolute right-4 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/50 hover:bg-black/80 text-white z-20 cursor-pointer transition-all hover:scale-105 border border-white/10"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </button>
                      </>
                    )}
                  </div>

                  {/* Carrousel Footer Indicators */}
                  {selectedProject.assets.length > 1 && (
                    <div className="absolute bottom-4 inset-x-0 flex flex-col items-center gap-1.5 z-20">
                      <div className="flex gap-1.5">
                        {selectedProject.assets.map((_: any, idx: number) => (
                          <button
                            key={idx}
                            onClick={() => setCurrentMediaIndex(idx)}
                            className={`w-2 h-2 rounded-full transition-all cursor-pointer ${
                              idx === currentMediaIndex ? 'bg-white w-4' : 'bg-white/40 hover:bg-white/60'
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-[10px] font-bold text-white/70 bg-black/45 backdrop-blur px-2.5 py-0.5 rounded-full">
                        {currentMediaIndex + 1} de {selectedProject.assets.length}
                      </span>
                    </div>
                  )}
                </>
              ) : (
                // Gradient placeholder if no assets
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400 gap-4 bg-gradient-to-br from-slate-900 to-slate-950 w-full h-full relative">
                  <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-20"></div>
                  <FolderCheck className="w-16 h-16 text-violet-500/35" />
                  <p className="text-xs text-slate-500 italic">Nenhuma mídia anexada a este projeto.</p>
                </div>
              )}
            </div>

            {/* Right Information Panel */}
            <div className="w-full md:w-1/2 p-6 sm:p-8 flex flex-col justify-between overflow-y-auto max-h-[50vh] md:max-h-full">
              <div>
                {/* Header Row */}
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <span className="text-[10px] font-extrabold px-2.5 py-0.5 rounded-full bg-violet-100 text-violet-800 border border-violet-200/50 uppercase tracking-wider inline-block">
                      {selectedProject.project_type}
                    </span>
                    <h3 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight mt-1.5">
                      {selectedProject.name}
                    </h3>
                  </div>
                  <button 
                    onClick={() => setSelectedProject(null)}
                    className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer shrink-0"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Case Story / Scope */}
                <div className="mt-6 space-y-3">
                  <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Sobre o Case</h4>
                  <p className="text-sm text-slate-600 leading-relaxed break-words font-medium whitespace-pre-line">
                    {selectedProject.description || 'Descrição detalhada do projeto não fornecida.'}
                  </p>
                </div>

                {/* Testimonial inside modal */}
                {projectTestimonial && (
                  <div className="mt-6 p-4 bg-amber-50/70 border border-amber-100/50 rounded-2xl space-y-3 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-bl-full -z-10"></div>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star 
                          key={star} 
                          className={`w-3.5 h-3.5 ${star <= projectTestimonial.rating ? 'text-amber-400 fill-amber-400' : 'text-slate-300'}`} 
                        />
                      ))}
                    </div>
                    <blockquote className="text-xs text-slate-600 font-semibold italic leading-relaxed break-words">
                      "{projectTestimonial.comment}"
                    </blockquote>
                    <div className="flex items-center gap-2.5 pt-1.5 border-t border-amber-100/40">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-amber-500 to-amber-600 text-white flex items-center justify-center font-bold text-xs uppercase">
                        {projectTestimonial.client_name.charAt(0)}
                      </div>
                      <div>
                        <h5 className="text-xs font-bold text-slate-800 leading-tight">{projectTestimonial.client_name}</h5>
                        <p className="text-[9px] text-slate-400 font-semibold mt-0.5">Avaliação do Cliente</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Footer specs / call to action */}
              <div className="mt-8 pt-5 border-t border-slate-100 flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-4 text-xs font-semibold text-slate-400">
                  <div>
                    <span className="block text-[9px] font-bold text-slate-300 uppercase tracking-wider">Status</span>
                    <span className={`inline-flex items-center gap-1.5 mt-0.5 ${
                      selectedProject.status === 'DELIVERED' || selectedProject.status === 'DEPLOYED' 
                        ? 'text-emerald-600 font-bold' 
                        : 'text-violet-600 font-bold'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        selectedProject.status === 'DELIVERED' || selectedProject.status === 'DEPLOYED'
                          ? 'bg-emerald-500'
                          : 'bg-violet-500'
                      }`} />
                      {selectedProject.status === 'DELIVERED' || selectedProject.status === 'DEPLOYED' ? 'Concluído' : 'Em Desenvolvimento'}
                    </span>
                  </div>
                </div>

                <div className="flex gap-2.5">
                  {selectedProject.deploy_url && (
                    <a
                      href={selectedProject.deploy_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl font-bold text-xs shadow-md transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Ver Sistema Online</span>
                    </a>
                  )}
                  <a
                    href="https://wa.me/5500000000000"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 bg-violet-600 hover:bg-violet-700 text-white px-5 py-2.5 rounded-xl font-bold text-xs shadow-md transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
                  >
                    <span>Solicitar Projeto Similar</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Footer */}
      {!isDashboard && <Footer onTabSelect={setActiveTab} />}
    </div>
  );
}

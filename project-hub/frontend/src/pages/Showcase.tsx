import { useState, useEffect } from 'react';
import { fetchShowcaseData } from '../services/api';
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
  Award
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Showcase() {
  const [data, setData] = useState<{ projects: any[]; testimonials: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'completed' | 'ongoing'>('completed');

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

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4 bg-slate-50 relative overflow-hidden">
        {/* Background Animation Bubbles */}
        <div className="animated-bg">
          <div className="bg-bubble-1"></div>
          <div className="bg-bubble-2"></div>
        </div>
        <Loader2 className="w-10 h-10 text-violet-600 animate-spin z-10" />
        <p className="text-slate-500 font-medium z-10">Carregando cases de sucesso...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-slate-50 relative overflow-hidden">
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

  return (
    <div className="min-h-screen bg-slate-50/50 pb-20 relative overflow-hidden">
      {/* Background Animation Bubbles */}
      <div className="animated-bg">
        <div className="bg-bubble-1"></div>
        <div className="bg-bubble-2"></div>
        <div className="bg-bubble-3"></div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 relative z-10">
        
        {/* Navigation / Brand Header */}
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
                {completedProjects.map((proj, idx) => (
                  <div key={idx} className="glass-card p-6 flex flex-col justify-between group hover:border-violet-300 hover:shadow-lg transition-all relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
                    <div className="space-y-4">
                      <div className="flex justify-between items-start gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-200/30 uppercase tracking-wider">
                          Pronto
                        </span>
                        <span className="text-xs font-semibold text-slate-400">
                          {proj.project_type}
                        </span>
                      </div>
                      <h3 className="text-lg font-bold text-slate-800 tracking-tight group-hover:text-violet-700 transition-colors">
                        {proj.name}
                      </h3>
                    </div>
                    <div className="pt-4 border-t border-slate-100/50 mt-6 flex items-center justify-between text-xs text-slate-400 font-semibold">
                      <span>Dominuslabs Case</span>
                      <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                    </div>
                  </div>
                ))}
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
                {ongoingProjects.map((proj, idx) => (
                  <div key={idx} className="glass-card p-6 flex flex-col justify-between group hover:border-violet-300 hover:shadow-lg transition-all relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-violet-500/5 rounded-bl-full -z-10 group-hover:scale-110 transition-transform"></div>
                    <div className="space-y-4">
                      <div className="flex justify-between items-start gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-violet-100 text-violet-800 border border-violet-200/30 uppercase tracking-wider">
                          Em Progresso
                        </span>
                        <span className="text-xs font-semibold text-slate-400">
                          {proj.project_type}
                        </span>
                      </div>
                      <h3 className="text-lg font-bold text-slate-800 tracking-tight group-hover:text-violet-700 transition-colors">
                        {proj.name}
                      </h3>
                    </div>
                    <div className="pt-4 border-t border-slate-100/50 mt-6 flex items-center justify-between text-xs text-slate-400 font-semibold">
                      <span>Desenvolvimento Ativo</span>
                      <TrendingUp className="w-3.5 h-3.5 text-violet-500" />
                    </div>
                  </div>
                ))}
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

      </div>

      {/* Footer */}
      <Footer onTabSelect={setActiveTab} />
    </div>
  );
}

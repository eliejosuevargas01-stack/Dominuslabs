import { Link } from 'react-router-dom';
import { 
  Heart, 
  Sparkles, 
  Mail, 
  MessageSquare, 
  ShieldCheck, 
  ArrowUp,
  ExternalLink,
  Laptop
} from 'lucide-react';

interface FooterProps {
  onTabSelect?: (tab: 'completed' | 'ongoing') => void;
}

export default function Footer({ onTabSelect }: FooterProps) {
  const handleScrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleTabClick = (tab: 'completed' | 'ongoing') => {
    if (onTabSelect) {
      onTabSelect(tab);
      handleScrollToTop();
    }
  };

  return (
    <footer className="w-full bg-slate-950 text-slate-400 mt-28 py-16 border-t border-slate-900 relative z-10 overflow-hidden">
      {/* Decorative ambient background glows */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-900/10 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-900/5 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Top Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-12 border-b border-slate-900">
          
          {/* Brand Info Column */}
          <div className="md:col-span-5 space-y-5">
            <div className="flex items-center gap-3">
              <div className="p-1.5 bg-gradient-to-tr from-violet-600 to-indigo-600 rounded-xl shadow-md shadow-violet-900/20">
                <img src="/logo.png" alt="Dominus Labs" className="w-7 h-7 object-contain" />
              </div>
              <span className="font-display font-extrabold text-2xl tracking-tight text-white">
                Dominuslabs
              </span>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed max-w-md">
              Especialistas em transformar ideias complexas em produtos digitais de alta conversão. Desenvolvemos Landing Pages premium, automações de processos, CRMs e soluções sob medida para escalar a sua operação.
            </p>
            
            {/* Server Status Indicator */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Sistemas Online & Operacionais
            </div>
          </div>

          {/* Solutions Column */}
          <div className="md:col-span-2.5 md:col-start-7 space-y-4">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-widest flex items-center gap-1.5">
              <Laptop className="w-3.5 h-3.5 text-violet-500" />
              Soluções
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li>
                <a 
                  href="https://wa.me/5500000000000" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="hover:text-white transition-colors duration-200 flex items-center gap-1 group"
                >
                  Landing Pages
                  <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              </li>
              <li>
                <a 
                  href="https://wa.me/5500000000000" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="hover:text-white transition-colors duration-200 flex items-center gap-1 group"
                >
                  Automações & APIs
                  <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              </li>
              <li>
                <a 
                  href="https://wa.me/5500000000000" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="hover:text-white transition-colors duration-200 flex items-center gap-1 group"
                >
                  Sistemas e CRMs
                  <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              </li>
              <li>
                <Link to="/cases" className="hover:text-white transition-colors duration-200">
                  Cases de Sucesso
                </Link>
              </li>
            </ul>
          </div>

          {/* Navigation Column */}
          <div className="md:col-span-2 space-y-4">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-widest flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Navegação
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li>
                {onTabSelect ? (
                  <button 
                    onClick={handleScrollToTop} 
                    className="hover:text-white transition-colors duration-200 cursor-pointer bg-transparent border-none p-0 text-left"
                  >
                    Início / Cases
                  </button>
                ) : (
                  <Link to="/cases" className="hover:text-white transition-colors duration-200">
                    Cases de Sucesso
                  </Link>
                )}
              </li>
              <li>
                {onTabSelect ? (
                  <button 
                    onClick={() => handleTabClick('completed')} 
                    className="hover:text-white transition-colors duration-200 cursor-pointer bg-transparent border-none p-0 text-left"
                  >
                    Cases Concluídos
                  </button>
                ) : (
                  <Link to="/cases" className="hover:text-white transition-colors duration-200">
                    Cases Concluídos
                  </Link>
                )}
              </li>
              <li>
                {onTabSelect ? (
                  <button 
                    onClick={() => handleTabClick('ongoing')} 
                    className="hover:text-white transition-colors duration-200 cursor-pointer bg-transparent border-none p-0 text-left"
                  >
                    Em Desenvolvimento
                  </button>
                ) : (
                  <Link to="/cases" className="hover:text-white transition-colors duration-200">
                    Em Progresso
                  </Link>
                )}
              </li>
            </ul>
          </div>

          {/* Contact Column */}
          <div className="md:col-span-2 space-y-4">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-widest flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-emerald-500" />
              Contato
            </h4>
            <ul className="space-y-2.5 text-sm">
              <li>
                <a 
                  href="https://wa.me/5500000000000" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="hover:text-white transition-colors duration-200 flex items-center gap-1 group font-semibold text-emerald-400"
                >
                  Falar no WhatsApp
                  <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              </li>
              <li className="flex items-center gap-1.5 text-slate-400">
                <Mail className="w-3.5 h-3.5 text-slate-500" />
                <span className="truncate">contato@dominuslabs.online</span>
              </li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="text-xs text-slate-500 space-y-1 text-center sm:text-left">
            <p>© {new Date().getFullYear()} Dominuslabs. Todos os direitos reservados.</p>
            <p className="flex items-center justify-center sm:justify-start gap-1">
              Feito com <Heart className="w-3 h-3 text-rose-500 fill-rose-500 animate-pulse" /> por 
              <span className="text-slate-400 font-semibold">Dominuslabs</span>
            </p>
          </div>
          
          <div className="flex items-center gap-6">
            <Link to="/login" className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1 font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-violet-500" />
              Acesso Restrito
            </Link>
            
            <button 
              onClick={handleScrollToTop}
              className="p-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white rounded-xl shadow-md transition-all duration-200 cursor-pointer"
              title="Voltar ao topo"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>
    </footer>
  );
}

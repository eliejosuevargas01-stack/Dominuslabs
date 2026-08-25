/**
 * Documentation-Driven Testing:
 * O comportamento esperado para Sidebar.tsx:
 * - Botões de Link: Navegam para as rotas corretas pelo react-router-dom sem reload (Spa).
 * - Botão Colapsar: Minimiza a largura e guarda valor no LocalStorage.
 * - Botão Logout: Limpa localStorage e redireciona ao '/login'.
 */

import { Link, useLocation } from 'react-router-dom';
import { Users, Folder, LogOut, Menu, X, PanelLeftClose, PanelLeftOpen, Briefcase, Radio, MessageSquare, Building2, BarChart2, Cpu, Workflow, Megaphone } from 'lucide-react';
import { useState } from 'react';

interface SidebarProps {
  handleLogout: () => void;
  isCollapsed: boolean;
  setIsCollapsed: (val: boolean) => void;
}

export default function Sidebar({ handleLogout, isCollapsed, setIsCollapsed }: SidebarProps) {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const menuItems = [
    { name: 'Resumo Operacional', path: '/dashboard-operacional', icon: BarChart2 },
    { name: 'Central Omnichannel', path: '/omnichannel', icon: MessageSquare },
    { name: 'CRM & Pipeline Pedidos', path: '/crm', icon: Users },
    { name: 'Consumo & IA', path: '/ia-inteligencia', icon: Cpu },
    { name: 'Automações & Regras', path: '/automacoes', icon: Workflow },
    { name: 'Campanhas Ativas', path: '/campanhas-wizard', icon: Megaphone },
    { name: 'Conexões & APIs', path: '/connections', icon: Radio },
    { name: 'Governança & Empresa', path: '/settings', icon: Building2 },
    { name: 'Cases & Portfólio', path: '/cases-dashboard', icon: Briefcase },
    { name: 'Project Hub', path: '/project-hub', icon: Folder },
  ];

  const isActive = (path: string) => {
    if (path === '/project-hub') {
      // Highlight Project Hub for any sub-routes of project-hub (like projects details)
      return location.pathname.startsWith('/project-hub') || location.pathname.startsWith('/admin');
    }
    return location.pathname === path;
  };

  return (
    <>
      {/* Mobile/Tablet Hamburger Button */}
      <div className="lg:hidden fixed top-3 left-4 z-50">
        <button
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? "Fechar menu" : "Abrir menu"}
          className="p-2 rounded-xl   border border-zinc-200 shadow-sm text-slate-700 hover:text-purple-700 transition-all cursor-pointer flex items-center justify-center"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Persistent Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 h-screen z-40 bg-white border-r border-zinc-200 flex flex-col justify-between transition-all duration-300 lg:transform-none overflow-x-hidden ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        } ${isCollapsed ? 'w-64 lg:w-20' : 'w-64 lg:w-64'}`}
      >
        {/* Logo and Menu Links */}
        <div className={`p-4 transition-all duration-300 ${isCollapsed ? 'lg:px-2' : ''}`}>
          <div className={`flex ${isCollapsed ? 'flex-col lg:items-center gap-4' : 'items-center justify-between'} mb-6 mt-4 lg:mt-0`}>
            <Link to="/project-hub" className="flex items-center gap-3 group">
              <img src="/logo.png" alt="Dominus Labs" className="w-8 h-8 rounded-lg object-contain shadow-sm group-hover:scale-105 transition-transform flex-shrink-0" />
              <span className={`font-display font-semibold text-xl tracking-tight text-zinc-900 transition-all duration-200 ${isCollapsed ? 'lg:hidden' : 'block'}`}>
                Dominuslabs
              </span>
            </Link>

            {/* Toggle Button for Desktop */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="hidden lg:flex p-1.5 rounded-lg border border-zinc-200 hover:bg-zinc-100 text-zinc-500 hover:text-zinc-900 transition-all cursor-pointer items-center justify-center bg-white shadow-sm"
              title={isCollapsed ? "Expandir menu" : "Recolher menu"}
            >
              {isCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
            </button>
          </div>

          <nav className={`space-y-1 ${isCollapsed ? 'lg:space-y-2' : ''}`}>
            {menuItems.map((item) => {
              const active = isActive(item.path);
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  title={item.name}
                  className={`flex items-center rounded-lg transition-all duration-200 group px-3 py-2.5 gap-3 ${
                    isCollapsed
                      ? 'lg:justify-center lg:w-10 lg:h-10 lg:p-0 lg:gap-0 lg:mx-auto'
                      : ''
                  } ${
                    active
                      ? 'bg-purple-50 text-purple-700'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
                  }`}
                >
                  <Icon className={`w-4 h-4 flex-shrink-0 ${active ? 'text-purple-600' : 'text-zinc-400 group-hover:text-zinc-600'}`} />
                  <span className={`font-medium text-sm whitespace-nowrap transition-all duration-200 ${isCollapsed ? 'lg:hidden' : 'block'}`}>
                    {item.name}
                  </span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom logout area */}
        <div className={`p-4 border-t border-zinc-200 space-y-4 transition-all duration-300 ${isCollapsed ? 'md:px-2' : ''}`}>
          <div className={`flex items-center gap-2 ${isCollapsed ? 'md:justify-center' : ''}`} title="Workstation">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0"></div>
            <span className={`text-[10px] uppercase tracking-wider font-semibold text-zinc-500 whitespace-nowrap transition-all duration-200 ${isCollapsed ? 'md:hidden' : 'block'}`}>
              Estação Corporativa
            </span>
          </div>

          <button
            onClick={() => {
              setIsOpen(false);
              handleLogout();
            }}
            title="Sair"
            className={`w-full flex items-center rounded-lg font-medium text-sm text-zinc-600 hover:text-red-600 hover:bg-red-50 transition-all cursor-pointer group px-3 py-2.5 gap-3 ${
              isCollapsed
                ? 'md:justify-center md:w-10 md:h-10 md:p-0 md:gap-0 md:mx-auto'
                : ''
            }`}
          >
            <LogOut className="w-4 h-4 text-zinc-400 group-hover:text-red-600 flex-shrink-0" />
            <span className={`transition-all duration-200 ${isCollapsed ? 'md:hidden' : 'block'}`}>
              Sair
            </span>
          </button>
        </div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          className="md:hidden fixed inset-0 z-30 bg-slate-900/20 "
        />
      )}
    </>
  );
}

import { Link, useLocation } from 'react-router-dom';
import { Search, Users, Folder, LogOut, Menu, X, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
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
    { name: 'Scrapper', path: '/scrapper', icon: Search },
    { name: 'CRM', path: '/crm', icon: Users },
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
      {/* Mobile Hamburguer Button */}
      <div className="md:hidden fixed top-3 left-4 z-50">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-2 rounded-xl bg-white/90 backdrop-blur-md border border-violet-100 shadow-sm text-slate-700 hover:text-purple-700 transition-all cursor-pointer flex items-center justify-center"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Persistent Sidebar */}
      <aside
        className={`fixed md:sticky top-0 left-0 h-screen z-40 bg-white/70 backdrop-blur-md border-r border-violet-100/50 shadow-md flex flex-col justify-between transition-all duration-300 md:transform-none overflow-x-hidden ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        } ${isCollapsed ? 'w-64 md:w-20' : 'w-64 md:w-64'}`}
      >
        {/* Logo and Menu Links */}
        <div className={`p-6 transition-all duration-300 ${isCollapsed ? 'md:px-2' : ''}`}>
          <div className={`flex ${isCollapsed ? 'flex-col md:items-center gap-4' : 'items-center justify-between'} mb-8 mt-4 md:mt-0`}>
            <Link to="/project-hub" className="flex items-center gap-2 group">
              <img src="/logo.png" alt="Dominus Labs" className="w-8 h-8 rounded-lg object-contain shadow-sm group-hover:scale-105 transition-transform flex-shrink-0" />
              <span className={`font-display font-extrabold text-2xl tracking-tight bg-gradient-to-r from-violet-800 via-indigo-700 to-emerald-600 bg-clip-text text-transparent transition-all duration-200 ${isCollapsed ? 'md:hidden' : 'block'}`}>
                Dominuslabs
              </span>
            </Link>

            {/* Toggle Button for Desktop */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="hidden md:flex p-1.5 rounded-lg border border-violet-100/50 hover:bg-violet-50 text-slate-400 hover:text-purple-700 transition-all cursor-pointer items-center justify-center bg-white shadow-sm"
              title={isCollapsed ? "Expandir menu" : "Recolher menu"}
            >
              {isCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
            </button>
          </div>

          <nav className={`space-y-1.5 ${isCollapsed ? 'md:space-y-3' : ''}`}>
            {menuItems.map((item) => {
              const active = isActive(item.path);
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  title={item.name}
                  className={`flex items-center rounded-xl transition-all duration-200 group px-4 py-3 gap-3 ${
                    isCollapsed
                      ? 'md:justify-center md:w-10 md:h-10 md:p-0 md:gap-0 md:mx-auto'
                      : ''
                  } ${
                    active
                      ? 'bg-gradient-to-r from-purple-700 to-indigo-600 text-white shadow-md shadow-purple-600/10'
                      : 'text-slate-600 hover:text-purple-700 hover:bg-violet-50/50 border border-transparent hover:border-violet-100/30'
                  }`}
                >
                  <Icon className={`w-4 h-4 transition-transform group-hover:scale-110 flex-shrink-0 ${active ? 'text-white' : 'text-slate-400 group-hover:text-purple-600'}`} />
                  <span className={`font-medium text-sm whitespace-nowrap transition-all duration-200 ${isCollapsed ? 'md:hidden' : 'block'}`}>
                    {item.name}
                  </span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom logout area */}
        <div className={`p-6 border-t border-violet-100/30 space-y-4 transition-all duration-300 ${isCollapsed ? 'md:px-2' : ''}`}>
          <div className={`flex items-center gap-2 ${isCollapsed ? 'md:justify-center' : ''}`} title="Workstation">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse flex-shrink-0"></div>
            <span className={`text-[10px] uppercase tracking-wider font-extrabold text-emerald-800 bg-emerald-100/80 border border-emerald-200/30 px-2.5 py-0.5 rounded-full whitespace-nowrap transition-all duration-200 ${isCollapsed ? 'md:hidden' : 'block'}`}>
              Workstation
            </span>
          </div>

          <button
            onClick={() => {
              setIsOpen(false);
              handleLogout();
            }}
            title="Sair"
            className={`w-full flex items-center rounded-xl font-semibold text-sm text-slate-500 hover:text-rose-600 bg-slate-100 hover:bg-rose-50 border border-slate-200/50 hover:border-rose-100 transition-all cursor-pointer group px-4 py-3 gap-3 ${
              isCollapsed
                ? 'md:justify-center md:w-10 md:h-10 md:p-0 md:gap-0 md:mx-auto'
                : ''
            }`}
          >
            <LogOut className="w-4 h-4 text-slate-400 group-hover:text-rose-600 transition-transform group-hover:translate-x-0.5 flex-shrink-0" />
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
          className="md:hidden fixed inset-0 z-30 bg-slate-900/20 backdrop-blur-sm"
        />
      )}
    </>
  );
}

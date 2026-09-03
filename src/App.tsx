/**
 * Documentation-Driven Testing:
 * O comportamento esperado para App.tsx:
 * - `ProtectedRoute`: Bloqueia o acesso sem `admin_token`, forçando redirecionamento `/login`.
 * - Rotas renderizam as páginas correspondentes envelopadas no `DashboardLayout` se autenticado.
 */

import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import AdminDashboard from './pages/AdminDashboard';
import AdminProjectView from './pages/AdminProjectView';
import PublicProjectView from './pages/PublicProjectView';
import Login from './pages/Login';
import OrderManagerView from './pages/OrderManagerView';

import Showcase from './pages/Showcase';
import Sidebar from './components/Sidebar';
import CrmView from './pages/CrmView';
import LeadDetailView from './pages/LeadDetailView';
import ConnectionsView from './pages/ConnectionsView';
import OmnichannelView from './pages/OmnichannelView';
import CompanySettingsView from './pages/CompanySettingsView';
import DashboardOperationalView from './pages/DashboardOperationalView';
import AiIntelligenceView from './pages/AiIntelligenceView';
import AutomationsView from './pages/AutomationsView';
import CampaignsWizardView from './pages/CampaignsWizardView';
import GlobalOrderNotification from './components/GlobalOrderNotification';
import { LogOut } from 'lucide-react';
import { Toaster } from 'sonner';
import './App.css';
import './index.css';

// Protected Route Wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("admin_token");
  if (!token || token === "null" || token === "undefined") {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_refresh_token");
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// Navigation Header Component
function Header() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const navigate = useNavigate();

  const checkAuth = () => {
    const token = localStorage.getItem("admin_token");
    setIsLoggedIn(!!token && token !== "null" && token !== "undefined");
  };

  useEffect(() => {
    checkAuth();
    window.addEventListener("storage", checkAuth);
    return () => window.removeEventListener("storage", checkAuth);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_refresh_token");
    setIsLoggedIn(false);
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-zinc-200 shadow-sm shrink-0">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/project-hub" className="flex items-center gap-2 group md:hidden ml-10">
          <img src="/logo.png" alt="Dominus Labs" className="w-8 h-8 rounded-lg object-contain shadow-sm group-hover:scale-105 transition-transform" />
          <span className="font-display font-semibold text-2xl tracking-tight text-zinc-900 group-hover:opacity-90 transition-opacity">
            Dominuslabs
          </span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <span className="hidden sm:flex text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Ambiente Interno Corporativo
          </span>

          {isLoggedIn && (
            <button
              onClick={handleLogout}
              className="text-xs font-medium text-zinc-500 hover:text-red-600 bg-zinc-50 hover:bg-red-50 border border-zinc-200 hover:border-red-100 px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 cursor-pointer md:hidden"
              title="Sair da Plataforma"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sair
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

// Layout wrapper for all logged-in views
function DashboardLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem('sidebar_collapsed') === 'true';
  });

  const toggleSidebar = (val: boolean) => {
    setIsCollapsed(val);
    localStorage.setItem('sidebar_collapsed', String(val));
  };

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_refresh_token");
    navigate("/login");
  };

  const isOmnichannel = location.pathname.includes('/omnichannel');

  return (
    <div className="flex min-h-screen relative w-full bg-zinc-50">
      <Sidebar handleLogout={handleLogout} isCollapsed={isCollapsed} setIsCollapsed={toggleSidebar} />
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        <Header />
        <main className={`flex-1 overflow-y-auto min-w-0 flex flex-col ${isOmnichannel ? 'p-0' : 'p-4 sm:p-6 lg:p-8'}`}>
          <div className={`w-full flex-1 flex flex-col ${isOmnichannel ? 'h-full max-w-none' : 'max-w-7xl mx-auto'}`}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen text-zinc-900 font-sans relative">
        <Toaster position="top-right" richColors closeButton />
        <GlobalOrderNotification />

        <Routes>
          {/* Public Access Routes (no sidebar layout) */}
          <Route path="/login" element={<Login />} />
          <Route path="/project/:public_token" element={<PublicProjectView />} />
          <Route path="/cases" element={<Showcase />} />

          {/* Protected Admin Routes (with sidebar layout) */}
          <Route
            path="/project-hub"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <AdminDashboard />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/order-manager"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <OrderManagerView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard-operacional"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <DashboardOperationalView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/ia-inteligencia"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <AiIntelligenceView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/automacoes"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <AutomationsView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/campanhas-wizard"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <CampaignsWizardView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <CompanySettingsView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/project-hub/project/:id"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <AdminProjectView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/omnichannel"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <OmnichannelView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/crm"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <CrmView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/connections"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <ConnectionsView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases-dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Showcase isDashboard={true} />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/crm/leads/:id"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <LeadDetailView />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          {/* Default fallback redirects */}
          <Route path="/admin/*" element={<Navigate to="/dashboard-operacional" replace />} />
          <Route path="/admin" element={<Navigate to="/dashboard-operacional" replace />} />
          <Route path="/" element={<Navigate to="/dashboard-operacional" replace />} />
          <Route path="*" element={<Navigate to="/dashboard-operacional" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export { ProtectedRoute };
export default App;
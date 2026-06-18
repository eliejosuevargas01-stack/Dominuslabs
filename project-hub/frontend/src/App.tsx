import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import AdminDashboard from './pages/AdminDashboard';
import AdminProjectView from './pages/AdminProjectView';
import PublicProjectView from './pages/PublicProjectView';
import Login from './pages/Login';
import Showcase from './pages/Showcase';
import Sidebar from './components/Sidebar';
import ScrapperView from './pages/ScrapperView';
import CrmView from './pages/CrmView';
import LeadDetailView from './pages/LeadDetailView';
import ConnectionsView from './pages/ConnectionsView';
import { LogOut } from 'lucide-react';
import ChatPopup from './components/ChatPopup';
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
    <header className="sticky top-0 z-30 bg-white/70 backdrop-blur-md border-b border-violet-100 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/project-hub" className="flex items-center gap-2 group md:hidden ml-10">
          <img src="/logo.png" alt="Dominus Labs" className="w-8 h-8 rounded-lg object-contain shadow-sm group-hover:scale-105 transition-transform" />
          <span className="font-display font-extrabold text-2xl tracking-tight bg-gradient-to-r from-violet-800 via-indigo-700 to-emerald-600 bg-clip-text text-transparent group-hover:opacity-90 transition-opacity">
            Dominuslabs
          </span>
        </Link>
        
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="hidden sm:flex text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200 items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            Internal Workstation
          </span>

          {isLoggedIn && (
            <button
              onClick={handleLogout}
              className="text-xs font-semibold text-slate-500 hover:text-rose-600 bg-slate-100 hover:bg-rose-50 border border-slate-200/50 hover:border-rose-100 px-3.5 py-1.5 rounded-xl transition-all flex items-center gap-1.5 cursor-pointer md:hidden"
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

  return (
    <div className="flex min-h-screen relative z-10 w-full">
      <Sidebar handleLogout={handleLogout} isCollapsed={isCollapsed} setIsCollapsed={toggleSidebar} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
      <ChatPopup />
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen text-slate-800 font-sans relative">
        {/* Background Animation Bubbles */}
        <div className="animated-bg">
          <div className="bg-bubble-1"></div>
          <div className="bg-bubble-2"></div>
          <div className="bg-bubble-3"></div>
        </div>

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
            path="/scrapper" 
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <ScrapperView />
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
          <Route path="/admin/*" element={<Navigate to="/project-hub" replace />} />
          <Route path="/admin" element={<Navigate to="/project-hub" replace />} />
          <Route path="/" element={<Navigate to="/project-hub" replace />} />
          <Route path="*" element={<Navigate to="/project-hub" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
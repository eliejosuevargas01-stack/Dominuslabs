import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import AdminDashboard from './pages/AdminDashboard';
import AdminProjectView from './pages/AdminProjectView';
import PublicProjectView from './pages/PublicProjectView';
import Login from './pages/Login';
import { LogOut, Sparkles } from 'lucide-react';
import './App.css';
import './index.css';

// Protected Route Wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("admin_token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// Navigation Header Component that reacts to auth changes
function Header() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const navigate = useNavigate();

  const checkAuth = () => {
    setIsLoggedIn(!!localStorage.getItem("admin_token"));
  };

  useEffect(() => {
    checkAuth();
    // Listen to localstorage updates or navigation events
    window.addEventListener("storage", checkAuth);
    return () => window.removeEventListener("storage", checkAuth);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    setIsLoggedIn(false);
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-50 bg-white/70 backdrop-blur-md border-b border-violet-100 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/admin" className="flex items-center gap-2 group">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-700 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-md group-hover:scale-105 transition-transform">
            D
          </span>
          <span className="font-display font-extrabold text-2xl tracking-tight bg-gradient-to-r from-violet-800 via-indigo-700 to-emerald-600 bg-clip-text text-transparent group-hover:opacity-90 transition-opacity">
            Dominuslabs
          </span>
        </Link>
        
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            Internal Workstation
          </span>

          {isLoggedIn && (
            <button
              onClick={handleLogout}
              className="text-xs font-semibold text-slate-500 hover:text-rose-600 bg-slate-100 hover:bg-rose-50 border border-slate-200/50 hover:border-rose-100 px-3.5 py-1.5 rounded-xl transition-all flex items-center gap-1.5 cursor-pointer"
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

function App() {
  return (
    <Router>
      <div className="min-h-screen text-slate-800 font-sans pb-12 relative">
        {/* Background Animation Bubbles */}
        <div className="animated-bg">
          <div className="bg-bubble-1"></div>
          <div className="bg-bubble-2"></div>
          <div className="bg-bubble-3"></div>
        </div>

        {/* Premium Glassmorphic Header */}
        <Header />

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 relative z-10">
          <Routes>
            {/* Public Access Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/project/:public_token" element={<PublicProjectView />} />

            {/* Protected Admin Routes */}
            <Route 
              path="/admin" 
              element={
                <ProtectedRoute>
                  <AdminDashboard />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/admin/project/:id" 
              element={
                <ProtectedRoute>
                  <AdminProjectView />
                </ProtectedRoute>
              } 
            />

            {/* Default fallback redirects */}
            <Route path="/" element={<Navigate to="/admin" replace />} />
            <Route path="*" element={<Navigate to="/admin" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AdminDashboard from './pages/AdminDashboard';
import AdminProjectView from './pages/AdminProjectView';
import PublicProjectView from './pages/PublicProjectView';
import './App.css';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100 text-gray-900 font-sans">
        {/* Simple Navbar for Admin */}
        <nav className="bg-blue-800 text-white p-4 shadow-md">
          <div className="max-w-7xl mx-auto font-bold text-xl">
            Project Hub
          </div>
        </nav>

        <main className="max-w-7xl mx-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/admin" replace />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/project/:id" element={<AdminProjectView />} />
            <Route path="/project/:public_token" element={<PublicProjectView />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
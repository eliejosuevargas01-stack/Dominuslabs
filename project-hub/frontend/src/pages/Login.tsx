import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser } from '../services/api';
import { Lock, User, Loader2, Sparkles } from 'lucide-react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // If already logged in, redirect to admin
    const token = localStorage.getItem("admin_token");
    if (token) {
      navigate('/admin');
    }
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Por favor preencha todos os campos.');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const data = await loginUser(username.trim(), password.trim());
      localStorage.setItem("admin_token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("admin_refresh_token", data.refresh_token);
      }
      navigate('/admin');
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Credenciais inválidas. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-[70vh] px-4 animate-[fade-in_0.4s_ease-out]">
      <div className="w-full max-w-md glass-card p-8 space-y-6 relative overflow-hidden border border-violet-100/50">

        {/* Glow effect */}
        <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-violet-500/10 to-emerald-500/10 rounded-full blur-xl -z-10"></div>
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-gradient-to-tr from-amber-500/10 to-violet-500/10 rounded-full blur-xl -z-10"></div>

        {/* Heading Logo */}
        <div className="text-center space-y-2">
          <img src="/logo.png" alt="Dominus Labs" className="mx-auto w-12 h-12 rounded-2xl object-contain shadow-lg" />
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-violet-800 to-indigo-700 bg-clip-text text-transparent">
            Dominuslabs
          </h1>
          <p className="text-xs text-slate-400 font-semibold tracking-wider uppercase flex items-center justify-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Internal workstation
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-100 rounded-xl text-rose-700 text-xs font-semibold text-center">
              {error}
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-slate-400" />
              Usuário
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="ex: admin"
              className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 bg-white/70 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
              disabled={loading}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              Senha
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 bg-white/70 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="btn-primary w-full flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-bold shadow-md cursor-pointer hover:scale-[1.01] active:scale-[0.99] transition-all disabled:opacity-50 mt-2"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Entrando...
              </>
            ) : (
              'Entrar na Plataforma'
            )}
          </button>
        </form>

        {/* Footer info */}
        <p className="text-[10px] text-center text-slate-400 font-medium">
          Acesso restrito ao administrador da Dominuslabs.
        </p>

      </div>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

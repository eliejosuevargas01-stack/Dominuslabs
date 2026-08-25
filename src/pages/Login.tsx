/**
 * Documentation-Driven Testing:
 * O comportamento esperado para Login.tsx:
 * - Botão 'Acessar Plataforma': Ao clicar, aciona `loginUser`. Exibe um loader de loading enquanto processa a requisição.
 * - Inputs (Usuário/Senha): Validam e atualizam o estado React (`username`, `password`).
 * - Tratamento de erro: Se o login falhar, um toast (Sonner) será disparado.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser } from '../services/api';
import { Lock, User, Loader2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

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
      navigate('/project-hub');
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
      if (data.whatsapp_token) {
        localStorage.setItem("whatsapp_token", data.whatsapp_token);
      }
      navigate('/project-hub');
      toast.success('Login efetuado com sucesso!');
    } catch (err: unknown) {
      const errorMessage = 'Credenciais inválidas ou erro no servidor. Tente novamente.';
      toast.error(errorMessage);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-[70vh] px-4 animate-[fade-in_0.4s_ease-out]">
      <div className="w-full max-w-md surface-card p-8 space-y-6 relative overflow-hidden border border-zinc-200/50">
        
        {/* Glow effect */}
        <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-purple-500/10 to-emerald-500/10 rounded-full blur-xl -z-10"></div>
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-gradient-to-tr from-amber-500/10 to-purple-500/10 rounded-full blur-xl -z-10"></div>

        {/* Heading Logo */}
        <div className="text-center space-y-2">
          <img src="/logo.png" alt="Dominus Labs" className="mx-auto w-12 h-12 rounded-2xl object-contain shadow-lg" />
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-purple-800 to-indigo-700 bg-clip-text text-transparent">
            Dominuslabs
          </h1>
          <p className="text-xs text-zinc-400 font-semibold tracking-wider uppercase flex items-center justify-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Portal Corporativo de Alta Performance
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
            <label htmlFor="username" className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-zinc-400" />
              Usuário
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="ex: admin"
              autoComplete="username"
              className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2.5  focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
              disabled={loading}
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="password" className="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-zinc-400" />
              Senha
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2.5  focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
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
        <p className="text-[10px] text-center text-zinc-400 font-medium">
          Acesso estritamente autenticado e monitorado. Criptografia ponta a ponta Dominus Labs.
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

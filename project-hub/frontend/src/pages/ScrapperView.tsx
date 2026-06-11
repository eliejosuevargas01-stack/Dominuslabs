import { useState } from 'react';
import { Play, Loader2, Check, AlertCircle, Sparkles } from 'lucide-react';
import { API_BASE, fetchWithAuth } from '../services/api';

export default function ScrapperView() {
  const [queries, setQueries] = useState('');
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [minResults, setMinResults] = useState(10);
  const [maxResults, setMaxResults] = useState(100);
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const availablePlatforms = [
    { id: 'whatsapp', label: 'WhatsApp' },
    { id: 'instagram', label: 'Instagram' },
    { id: 'email', label: 'E-mail' },
    { id: 'phone', label: 'Telefone' }
  ];

  const handleTogglePlatform = (id: string) => {
    if (platforms.includes(id)) {
      setPlatforms(platforms.filter(p => p !== id));
    } else {
      setPlatforms([...platforms, id]);
    }
  };

  const handleRunSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccess(null);
    setError(null);

    // Split queries by new line and filter empty lines
    const queriesList = queries
      .split('\n')
      .map(q => q.trim())
      .filter(q => q.length > 0);

    if (queriesList.length === 0) {
      setError('Por favor, insira pelo menos uma query de busca.');
      setLoading(false);
      return;
    }

    if (platforms.length === 0) {
      setError('Selecione pelo menos uma plataforma de busca.');
      setLoading(false);
      return;
    }

    const payload = {
      queries: queriesList,
      platforms: platforms,
      min_results: Number(minResults),
      max_results: Number(maxResults)
    };

    try {
      const response = await fetchWithAuth(`${API_BASE}/scrapper/run`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Falha ao conectar com o N8N');
      }

      setSuccess('Busca iniciada com sucesso! O workflow do N8N está processando os leads em segundo plano.');
      // Optional: Clear form on success
      setQueries('');
      setPlatforms([]);
    } catch (err: any) {
      setError(err.message || 'Erro ao tentar iniciar a busca.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-violet-600 animate-pulse" />
            Lead Scrapper
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure e inicie buscas automáticas de leads através dos workflows do N8N.
          </p>
        </div>
      </div>

      {/* Main Glassmorphic Form Card */}
      <div className="glass-card p-6 sm:p-8 bg-white/70 backdrop-blur-md border border-violet-100/30 rounded-2xl shadow-xl">
        <form onSubmit={handleRunSearch} className="space-y-6">
          {/* Queries Area */}
          <div className="space-y-2">
            <label className="block text-sm font-bold text-slate-700" htmlFor="queries">
              Termos de Busca (Queries)
            </label>
            <textarea
              id="queries"
              rows={4}
              value={queries}
              onChange={(e) => setQueries(e.target.value)}
              placeholder={`energia solar\ndentista\nadvogado imigração`}
              className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-white/50 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-200/50 outline-none transition-all placeholder:text-slate-400 text-sm font-medium"
            />
            <p className="text-[11px] text-slate-400">
              Insira um termo por linha. O robô executará uma busca para cada termo listado.
            </p>
          </div>

           {/* Platforms Multi-Select */}
          <div className="space-y-2">
            <label className="block text-sm font-bold text-slate-700">
              Canais de Contato Exigidos (Plataformas Alvo)
            </label>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {availablePlatforms.map((platform) => {
                const selected = platforms.includes(platform.id);
                return (
                  <button
                    key={platform.id}
                    type="button"
                    onClick={() => handleTogglePlatform(platform.id)}
                    className={`flex items-center justify-between p-3 rounded-xl border text-left text-xs font-semibold transition-all cursor-pointer ${
                      selected
                        ? 'border-purple-500 bg-purple-50 text-purple-700 shadow-sm'
                        : 'border-violet-100 bg-white/50 hover:bg-white hover:border-violet-200 text-slate-600'
                    }`}
                  >
                    <span>{platform.label}</span>
                    {selected && (
                      <span className="w-4 h-4 rounded-full bg-purple-600 flex items-center justify-center text-white">
                        <Check className="w-2.5 h-2.5" />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-slate-400">
              O scrapper buscará apenas leads que possuam pelo menos um dos meios de contato selecionados acima.
            </p>
          </div>

          {/* Numeric Limits */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-bold text-slate-700" htmlFor="minResults">
                Mínimo de Resultados
              </label>
              <input
                id="minResults"
                type="number"
                min={1}
                value={minResults}
                onChange={(e) => setMinResults(Number(e.target.value))}
                className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-white/50 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-200/50 outline-none transition-all text-sm font-semibold"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-bold text-slate-700" htmlFor="maxResults">
                Máximo de Resultados
              </label>
              <input
                id="maxResults"
                type="number"
                min={minResults}
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-white/50 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-200/50 outline-none transition-all text-sm font-semibold"
              />
            </div>
          </div>

          {/* Error and Success Banners */}
          {error && (
            <div className="flex items-center gap-2 p-3.5 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-xs font-semibold">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 p-3.5 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800 text-xs font-semibold">
              <Check className="w-4 h-4 shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-bold text-sm bg-gradient-to-r from-purple-700 to-indigo-600 hover:from-purple-800 hover:to-indigo-700 shadow-lg shadow-purple-700/10 hover:shadow-xl hover:shadow-purple-700/20 active:scale-95 disabled:opacity-50 transition-all cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Iniciando busca...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Executar Busca</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

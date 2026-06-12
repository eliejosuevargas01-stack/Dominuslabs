import { useState, useEffect } from 'react';
import { Play, Loader2, Check, AlertCircle, Sparkles, MapPin, Target, Webhook } from 'lucide-react';
import { API_BASE, fetchWithAuth } from '../services/api';

export default function ScrapperView() {
  const [activeTab, setActiveTab] = useState<'meta' | 'maps'>('meta');

  // Shared state
  const [queries, setQueries] = useState(() => localStorage.getItem('scrapper_queries') || '');

  useEffect(() => {
    localStorage.setItem('scrapper_queries', queries);
  }, [queries]);
  const [webhookUrl, setWebhookUrl] = useState('');
  
  // Meta Ads specific state
  const [metaMinResults, setMetaMinResults] = useState(5);
  const [metaMaxResults, setMetaMaxResults] = useState(20);
  const [targetPlatform, setTargetPlatform] = useState('');

  // Google Maps specific state
  const [mapsMaxResults, setMapsMaxResults] = useState(50);

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccess(null);
    setError(null);

    const queriesList = queries
      .split('\n')
      .map(q => q.trim())
      .filter(q => q.length > 0);

    if (queriesList.length === 0) {
      setError('Por favor, insira pelo menos uma query de busca.');
      setLoading(false);
      return;
    }

    let payload: any = {
      queries: queriesList,
    };

    if (webhookUrl.trim() !== '') {
      payload.webhook_url = webhookUrl.trim();
    }

    let endpoint = '';

    if (activeTab === 'meta') {
      endpoint = '/scrape/meta_ads';
      payload.min_results = Number(metaMinResults);
      payload.max_results = Number(metaMaxResults);
      if (targetPlatform) {
        payload.target_platform = targetPlatform;
      }
    } else {
      endpoint = '/scrape/google_maps';
      payload.max_results = Number(mapsMaxResults);
    }

    try {
      const response = await fetchWithAuth(`${API_BASE}${endpoint}`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Falha ao conectar com o N8N');
      }

      setSuccess(`Busca iniciada com sucesso! O webhook (${activeTab === 'meta' ? 'Meta Ads' : 'Google Maps'}) foi acionado.`);
      setQueries('');
      // Optional reset
    } catch (err: any) {
      setError(err.message || 'Erro ao tentar iniciar a busca.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-violet-600 animate-pulse" />
            Lead Scrapper
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure e inicie buscas automáticas de leads em diferentes plataformas através dos workflows do N8N.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex bg-white/50 backdrop-blur-md p-1.5 rounded-2xl border border-violet-100 shadow-sm w-fit">
        <button
          onClick={() => setActiveTab('meta')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all ${
            activeTab === 'meta'
              ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
              : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100/50'
          }`}
        >
          <Target className="w-4 h-4" />
          Meta Ads Library
        </button>
        <button
          onClick={() => setActiveTab('maps')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all ${
            activeTab === 'maps'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
              : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100/50'
          }`}
        >
          <MapPin className="w-4 h-4" />
          Google Maps
        </button>
      </div>

      {/* Form Card */}
      <div className="glass-card p-6 sm:p-8 bg-white/70 backdrop-blur-md border border-violet-100/30 rounded-2xl shadow-xl transition-all">
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
              placeholder={activeTab === 'meta' ? 'rinoplastia bh\nharmonizacao facial' : 'restaurante italiano em são paulo\npizzaria em belo horizonte'}
              className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-white/50 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-200/50 outline-none transition-all placeholder:text-slate-400 text-sm font-medium resize-none"
            />
            <p className="text-[11px] text-slate-400">
              Insira um termo por linha. Obrigatório.
            </p>
          </div>

          {/* Meta Ads Specific Fields */}
          {activeTab === 'meta' && (
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-bold text-slate-700" htmlFor="metaMinResults">
                    Mínimo de Resultados
                  </label>
                  <input
                    id="metaMinResults"
                    type="number"
                    min={1}
                    value={metaMinResults}
                    onChange={(e) => setMetaMinResults(Number(e.target.value))}
                    className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-white/50 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-200/50 outline-none transition-all text-sm font-semibold"
                  />
                  <p className="text-[11px] text-slate-400">Padrão: 5</p>
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-bold text-slate-700" htmlFor="metaMaxResults">
                    Máximo de Resultados
                  </label>
                  <input
                    id="metaMaxResults"
                    type="number"
                    min={metaMinResults}
                    value={metaMaxResults}
                    onChange={(e) => setMetaMaxResults(Number(e.target.value))}
                    className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-white/50 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-200/50 outline-none transition-all text-sm font-semibold"
                  />
                  <p className="text-[11px] text-slate-400">Padrão: 20</p>
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-700">
                  Target Platform (Opcional)
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: '', label: 'Qualquer' },
                    { id: 'whatsapp', label: 'WhatsApp' },
                    { id: 'site_externo', label: 'Site Externo' }
                  ].map((platform) => {
                    const selected = targetPlatform === platform.id;
                    return (
                      <button
                        key={platform.id}
                        type="button"
                        onClick={() => setTargetPlatform(platform.id)}
                        className={`flex items-center justify-center p-3 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                          selected
                            ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-sm'
                            : 'border-violet-100 bg-white/50 hover:bg-white hover:border-violet-200 text-slate-600'
                        }`}
                      >
                        {platform.label}
                      </button>
                    );
                  })}
                </div>
                <p className="text-[11px] text-slate-400">
                  Filtra os anúncios por destino. Ex: Apenas anúncios que mandam direto para o WhatsApp.
                </p>
              </div>
            </div>
          )}

          {/* Google Maps Specific Fields */}
          {activeTab === 'maps' && (
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="space-y-2">
                <label className="block text-sm font-bold text-slate-700" htmlFor="mapsMaxResults">
                  Máximo de Resultados
                </label>
                <input
                  id="mapsMaxResults"
                  type="number"
                  min={1}
                  value={mapsMaxResults}
                  onChange={(e) => setMapsMaxResults(Number(e.target.value))}
                  className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-white/50 focus:bg-white focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200/50 outline-none transition-all text-sm font-semibold"
                />
                <p className="text-[11px] text-slate-400">Padrão: 50. O Google Maps não utiliza target_platform.</p>
              </div>
            </div>
          )}

          {/* Webhook Override */}
          <div className="space-y-2 pt-4 border-t border-violet-100/50">
            <label className="flex items-center gap-1.5 text-sm font-bold text-slate-700" htmlFor="webhookUrl">
              <Webhook className="w-4 h-4 text-slate-400" />
              Webhook URL (Override)
            </label>
            <input
              id="webhookUrl"
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://myn8n.seommerce.shop/webhook/scrapper"
              className="w-full px-4 py-3 rounded-xl border border-violet-100 bg-slate-50 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-200/50 outline-none transition-all text-xs font-medium placeholder:text-slate-400"
            />
            <p className="text-[11px] text-slate-400">
              Opcional. Se vazio, o backend usará a URL padrão configurada no ambiente. Útil para debugar rotas diferentes.
            </p>
          </div>

          {/* Error and Success Banners */}
          {error && (
            <div className="flex items-center gap-2 p-3.5 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-xs font-semibold animate-in zoom-in-95 duration-200">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 p-3.5 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800 text-xs font-semibold animate-in zoom-in-95 duration-200">
              <Check className="w-4 h-4 shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className={`w-full flex items-center justify-center gap-2 py-3.5 rounded-xl text-white font-bold text-sm shadow-lg active:scale-[0.98] disabled:opacity-50 transition-all cursor-pointer ${
              activeTab === 'meta' 
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-blue-600/20 hover:shadow-blue-600/30'
                : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 shadow-emerald-600/20 hover:shadow-emerald-600/30'
            }`}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Enviando...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Disparar {activeTab === 'meta' ? 'Meta Ads' : 'Google Maps'}</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

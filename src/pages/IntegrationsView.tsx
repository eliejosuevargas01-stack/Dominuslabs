/**
 * Documentation-Driven Testing:
 * - Cards de Integração: Exibem status Conectado/Disponivel com toggle e ações.
 * - Modal Conectar: Cria nova integração via POST /integrations com toast.
 * - Desconectar: Confirmação inline antes de DELETE.
 * - Toggle: Ativa/desativa via PATCH /integrations/{id}.
 */

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Truck, Trash2, Loader2, X, AlertCircle,
} from 'lucide-react';

import {
  fetchIntegrations,
  createIntegration,
  deleteIntegration,
  patchIntegration,
  type Integration,
} from '../services/api';

interface ConfirmState {
  id: number;
  platform: string;
}

const PLATFORMS = [
  { key: 'pedidos10', label: 'Pedidos10' },
  { key: 'ifood', label: 'iFood' },
  { key: 'aiqfome', label: 'aiqfome' },
] as const;

const PLATFORM_LABELS: Record<string, string> = {
  pedidos10: 'Pedidos10',
  ifood: 'iFood',
  aiqfome: 'aiqfome',
};

export default function IntegrationsView() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectOpen, setConnectOpen] = useState(false);
  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<ConfirmState | null>(null);

  const [storeCode, setStoreCode] = useState('');
  const [displayName, setDisplayName] = useState('');

  const loadIntegrations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchIntegrations();
      setIntegrations(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar integrações.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIntegrations();
  }, [loadIntegrations]);

  const openConnect = (platform: string) => {
    setConnectingPlatform(platform);
    setStoreCode('');
    setDisplayName('');
    setConnectOpen(true);
  };

  const handleConnect = async () => {
    if (!connectingPlatform || !storeCode.trim()) {
      toast.error('Informe o código da loja.');
      return;
    }
    try {
      await createIntegration(
        connectingPlatform,
        storeCode.trim(),
        displayName.trim() || undefined,
      );
      toast.success('Integração criada com sucesso!');
      setConnectOpen(false);
      setConnectingPlatform(null);
      loadIntegrations();
    } catch (err: any) {
      toast.error(err.message || 'Falha ao conectar integração.');
    }
  };

  const requestDelete = (integration: Integration) => {
    setConfirmDelete({
      id: integration.id,
      platform: integration.platform,
    });
  };

  const confirmAndDelete = async () => {
    if (!confirmDelete) return;
    try {
      await deleteIntegration(confirmDelete.id);
      toast.success('Integração desconectada com sucesso!');
      setConfirmDelete(null);
      loadIntegrations();
    } catch (err: any) {
      toast.error(err.message || 'Falha ao desconectar.');
    }
  };

  const cancelDelete = () => {
    setConfirmDelete(null);
  };

  const toggleActive = async (integration: Integration) => {
    try {
      await patchIntegration(integration.id, !integration.is_active);
      toast.success(
        integration.is_active
          ? 'Integração desativada.'
          : 'Integração ativada.',
      );
      loadIntegrations();
    } catch (err: any) {
      toast.error(err.message || 'Falha ao atualizar status.');
    }
  };

  const getIntegrationForPlatform = (platform: string): Integration | undefined =>
    integrations.find((i) => i.platform === platform);

  const platformDisplayName = (platform: string): string =>
    PLATFORM_LABELS[platform] || platform;

  return (
    <div className="w-full flex-1 flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-black text-zinc-900 tracking-tight">
          Integrações de Delivery
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          Conecte suas plataformas de delivery para sincronizar pedidos e estoque
          automaticamente.
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 flex items-center gap-2.5 p-3.5 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-xs font-semibold">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
          <span>{error}</span>
          <button
            onClick={loadIntegrations}
            className="ml-auto text-zinc-400 hover:text-rose-700 transition-colors"
          >
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          </button>
        </div>
      )}

      {/* Grid */}
      {loading && integrations.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] surface-card">
          <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
          <p className="text-sm text-zinc-400 mt-2 font-medium">
            Carregando integrações...
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PLATFORMS.map((platform) => {
            const integration = getIntegrationForPlatform(platform.key);
            const connected = !!integration;
            const active = connected && integration!.is_active;

            return (
              <div
                key={platform.key}
                className="surface-card p-6 border border-zinc-200/30 flex flex-col"
              >
                {/* Header do card */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
                      <Truck className="w-5 h-5" />
                    </div>
                    <span className="font-bold text-zinc-800">
                      {platform.label}
                    </span>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                      active
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : connected
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-zinc-100 text-zinc-500 border border-zinc-200'
                    }`}
                  >
                    {active ? 'Conectado' : connected ? 'Inativo' : 'Disponível'}
                  </span>
                </div>

                {/* Body do card */}
                {connected ? (
                  <div className="flex-1 space-y-3 text-sm text-zinc-600">
                    {integration!.display_name && (
                      <p>
                        <span className="font-medium">Nome:</span>{' '}
                        {integration!.display_name}
                      </p>
                    )}
                    <p>
                      <span className="font-medium">Loja:</span>{' '}
                      {integration!.store_code}
                    </p>
                    {integration!.last_error && (
                      <div className="flex items-start gap-2 p-2.5 rounded-lg bg-rose-50 border border-rose-100 text-rose-700">
                        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>{integration!.last_error}</span>
                      </div>
                    )}

                    {/* Toggle ativo/inativo */}
                    <div className="flex items-center gap-2 pt-1">
                      <span className="text-xs font-medium text-zinc-500">
                        Status
                      </span>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={active}
                        onClick={() => toggleActive(integration!)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                          active
                            ? 'bg-purple-600'
                            : 'bg-zinc-300'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${
                            active ? 'translate-x-5' : 'translate-x-1'
                          }`}
                        />
                      </button>
                      <span className="text-xs text-zinc-500">
                        {active ? 'Ativo' : 'Inativo'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center min-h-[120px] text-center">
                    <p className="text-xs text-zinc-400">
                      Nenhuma conexão ativa para esta plataforma.
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="mt-4 flex gap-2">
                  {connected ? (
                    <>
                      <button
                        onClick={() => requestDelete(integration!)}
                        className="flex-1 flex items-center justify-center gap-1.5 bg-white border border-rose-200 text-rose-700 hover:bg-rose-50 rounded-xl px-4 py-2 text-sm font-bold transition-all cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                        Desconectar
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => openConnect(platform.key)}
                      className="w-full bg-gradient-to-r from-purple-700 to-indigo-600 text-white rounded-xl px-4 py-2 text-sm font-bold hover:opacity-95 transition-all cursor-pointer"
                    >
                      Conectar
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Conectar */}
      {connectOpen && connectingPlatform && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs"
          onClick={(e) => {
            if (e.target === e.currentTarget) setConnectOpen(false);
          }}
        >
          <div className="surface-card p-6 border border-zinc-200/30 w-full max-w-md mx-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-black text-zinc-800">
                Conectar {platformDisplayName(connectingPlatform)}
              </h2>
              <button
                onClick={() => {
                  setConnectOpen(false);
                  setConnectingPlatform(null);
                }}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-all cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-600 mb-1.5">
                  Código da loja
                </label>
                <input
                  type="text"
                  value={storeCode}
                  onChange={(e) => setStoreCode(e.target.value)}
                  placeholder="Digite o código da sua loja na plataforma"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-purple-200 text-sm text-zinc-800"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-600 mb-1.5">
                  Nome de exibição <span className="text-zinc-400">(opcional)</span>
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Como esta loja aparecerá na plataforma"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-purple-200 text-sm text-zinc-800"
                />
              </div>
            </div>

            <div className="flex gap-2.5 mt-6">
              <button
                onClick={() => {
                  setConnectOpen(false);
                  setConnectingPlatform(null);
                }}
                className="flex-1 text-sm font-medium text-zinc-600 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 rounded-xl px-4 py-2 transition-all cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleConnect}
                className="flex-1 bg-gradient-to-r from-purple-700 to-indigo-600 text-white rounded-xl px-4 py-2 text-sm font-bold hover:opacity-95 transition-all cursor-pointer"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmação inline de exclusão */}
      {confirmDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs"
          onClick={() => cancelDelete()}
        >
          <div
            className="surface-card p-5 border border-rose-200/50 w-full max-w-sm mx-2 text-center"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-12 h-12 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 mx-auto mb-3">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h3 className="text-base font-black text-zinc-800 mb-1">
              Confirmar desconexão
            </h3>
            <p className="text-sm text-zinc-500 mb-4">
              Tem certeza que deseja desconectar {'"'}
              {platformDisplayName(confirmDelete.platform)}
              {'"'}? Esta ação não pode ser desfeita.
            </p>
            <div className="flex gap-2.5">
              <button
                onClick={cancelDelete}
                className="flex-1 text-sm font-medium text-zinc-600 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 rounded-xl px-4 py-2 transition-all cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={confirmAndDelete}
                className="flex-1 bg-gradient-to-r from-rose-600 to-rose-500 text-white rounded-xl px-4 py-2 text-sm font-bold hover:opacity-95 transition-all cursor-pointer"
              >
                Desconectar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

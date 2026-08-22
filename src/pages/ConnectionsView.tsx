import React, { useState, useEffect, useCallback } from 'react';
import { 
  MessageSquare, Plus, Trash2, Wifi, WifiOff, Loader2, 
  AlertCircle, X, CheckCircle2, QrCode, ShieldAlert, Settings
} from 'lucide-react';

const Instagram = ({ size = 24, ...props }: React.SVGProps<SVGSVGElement> & { size?: number }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
    <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
  </svg>
);

import { 
  fetchWhatsappSessions, 
  createWhatsappSession, 
  connectWhatsappSession, 
  getWhatsappSessionStatus, 
  disconnectWhatsappSession, 
  deleteWhatsappSession,
  loginInstagramProxy,
  logoutInstagramProxy,
  getWhatsappSessionSettings,
  updateWhatsappSessionSettings,
} from '../services/api';

interface Session {
  id: string;
  name: string;
  platform: 'whatsapp' | 'instagram';
  snapshot?: {
    status?: string;
    qrAvailable?: boolean;
    qrDataUrl?: string | null;
  };
  stats?: {
    conversationCount: number;
    messageCount: number;
    unreadCount: number;
  };
}

export default function ConnectionsView() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WhatsApp Modal States
  const [isWaModalOpen, setIsWaModalOpen] = useState(false);
  const [waSessionName, setWaSessionName] = useState('');
  const [waCreating, setWaCreating] = useState(false);

  // Instagram Modal States
  const [isIgModalOpen, setIsIgModalOpen] = useState(false);
  const [igUsername, setIgUsername] = useState('');
  const [igPassword, setIgPassword] = useState('');
  const [igLoggingIn, setIgLoggingIn] = useState(false);

  // QR Code Modal States (Pairing)
  const [pairingSession, setPairingSession] = useState<Session | null>(null);
  const [qrCodeUrl, setQrCodeUrl] = useState<string | null>(null);
  const [pairingStatus, setPairingStatus] = useState<string>('');
  const [pollingActive, setPollingActive] = useState(false);

  // Webhook Settings Modal States
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [settingsSession, setSettingsSession] = useState<Session | null>(null);
  const [webhookEnabled, setWebhookEnabled] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [allowPrivate, setAllowPrivate] = useState(true);
  const [allowGroups, setAllowGroups] = useState(true);
  const [allowNewsletters, setAllowNewsletters] = useState(false);
  const [allowBroadcasts, setAllowBroadcasts] = useState(false);
  const [includeFromMe, setIncludeFromMe] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);

  // Credentials State
                      
  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchWhatsappSessions();
      const list = data?.sessions || (Array.isArray(data) ? data : []);
      setSessions(list);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Erro ao carregar conexões.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  

  
  
  // Helpers for extracting status and QR Code from various API response shapes
  const extractStatus = (res: any): string => {
    const raw = res?.session?.snapshot?.status || res?.snapshot?.status || res?.session?.status || res?.status || 'disconnected';
    return String(raw).toLowerCase();
  };

  const extractQrCode = (res: any): string | null => {
    const qr = res?.session?.snapshot?.qrDataUrl || res?.snapshot?.qrDataUrl || res?.session?.qrDataUrl || res?.qrDataUrl || res?.session?.snapshot?.qrCode || res?.snapshot?.qrCode || res?.qrCode || res?.qr;
    if (!qr) return null;
    if (typeof qr === 'string') {
      if (qr.startsWith('data:image') || qr.startsWith('http')) return qr;
      if (qr.length > 80 && !qr.includes(' ')) return `data:image/png;base64,${qr}`;
    }
    return qr;
  };

  // Polling for QR Code status check
  useEffect(() => {
    let intervalId: any = null;

    if (pollingActive && pairingSession) {
      intervalId = setInterval(async () => {
        try {
          const res = await getWhatsappSessionStatus(pairingSession.id);
          const currentStatus = extractStatus(res);
          setPairingStatus(currentStatus);

          const qrUrl = extractQrCode(res);
          if (qrUrl) {
            setQrCodeUrl(qrUrl);
          }

          if (currentStatus === 'connected') {
            setPollingActive(false);
            setQrCodeUrl(null);
            setTimeout(() => {
              setPairingSession(null);
              loadSessions();
            }, 1500);
          }
        } catch (err) {
          console.error('Error polling session status', err);
        }
      }, 3000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [pollingActive, pairingSession, loadSessions]);

  // Create WhatsApp Session Handler
  const handleCreateWaSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!waSessionName.trim()) return;

    try {
      setWaCreating(true);
      setError(null);
      const res = await createWhatsappSession(waSessionName.trim());
      setIsWaModalOpen(false);
      setWaSessionName('');
      
      // If session created, trigger connect immediately
      const createdSession = res?.session || (res?.id ? res : null);
      if (createdSession) {
        handleConnectWa(createdSession);
      } else {
        loadSessions();
      }
    } catch (err: any) {
      setError(err.message || 'Falha ao criar sessão do WhatsApp.');
    } finally {
      setWaCreating(false);
    }
  };

  // Connect WhatsApp Session (Open QR Modal)
  const handleConnectWa = async (session: Session) => {
    try {
      setError(null);
      setPairingSession(session);
      setQrCodeUrl(null);
      setPairingStatus('connecting');
      setPollingActive(true);

      const res = await connectWhatsappSession(session.id);
      const status = extractStatus(res);
      const qrUrl = extractQrCode(res);
      setPairingStatus(status);
      if (qrUrl) {
        setQrCodeUrl(qrUrl);
      }
    } catch (err: any) {
      setPollingActive(false);
      setPairingSession(null);
      setError(err.message || `Erro ao conectar sessão: ${session.name}`);
    }
  };

  // Disconnect Session
  const handleDisconnectWa = async (session: Session) => {
    if (!window.confirm(`Tem certeza que deseja desconectar o dispositivo da sessão "${session.name}"?`)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await disconnectWhatsappSession(session.id);
      loadSessions();
    } catch (err: any) {
      setError(err.message || `Erro ao desconectar dispositivo da sessão: ${session.name}`);
      setLoading(false);
    }
  };

  // Delete Session
  const handleDeleteWa = async (session: Session) => {
    if (!window.confirm(`ATENÇÃO: Deseja realmente excluir permanentemente a conexão "${session.name}" do servidor? Isso desconectará o aparelho e apagará todos os arquivos de sessão.`)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await deleteWhatsappSession(session.id);
      loadSessions();
    } catch (err: any) {
      setError(err.message || `Erro ao excluir sessão do servidor: ${session.name}`);
      setLoading(false);
    }
  };

  // Instagram Connection Form Submit
  const handleInstagramLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!igUsername.trim() || !igPassword.trim()) return;

    try {
      setIgLoggingIn(true);
      setError(null);
      await loginInstagramProxy({
        username: igUsername.trim(),
        password: igPassword
      });
      setIsIgModalOpen(false);
      setIgUsername('');
      setIgPassword('');
      loadSessions();
    } catch (err: any) {
      setError(err.message || 'Falha ao autenticar no Instagram. Verifique as credenciais.');
    } finally {
      setIgLoggingIn(false);
    }
  };

  // Webhook Settings Handlers
  const handleOpenSettings = async (session: Session) => {
    try {
      setSettingsSession(session);
      setIsSettingsModalOpen(true);
      setSettingsLoading(true);
      setError(null);

      const res = await getWhatsappSessionSettings(session.id);
      if (res && res.settings) {
        const wh = res.settings.webhook || {};
        setWebhookEnabled(!!wh.enabled);
        setWebhookUrl(wh.url || '');
        setWebhookSecret(wh.secret || '');
        setAllowPrivate(wh.allowPrivate !== false);
        setAllowGroups(wh.allowGroups !== false);
        setAllowNewsletters(!!wh.allowNewsletters);
        setAllowBroadcasts(!!wh.allowBroadcasts);
        setIncludeFromMe(!!wh.includeFromMe);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Falha ao carregar configurações.');
      setIsSettingsModalOpen(false);
    } finally {
      setSettingsLoading(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settingsSession) return;

    try {
      setSettingsSaving(true);
      setError(null);

      const payload = {
        webhook: {
          enabled: webhookEnabled,
          url: webhookUrl.trim(),
          secret: webhookSecret.trim(),
          allowPrivate,
          allowGroups,
          allowNewsletters,
          allowBroadcasts,
          includeFromMe
        }
      };

      await updateWhatsappSessionSettings(settingsSession.id, payload);
      setIsSettingsModalOpen(false);
      setSettingsSession(null);
    } catch (err: any) {
      setError(err.message || 'Falha ao salvar configurações.');
    } finally {
      setSettingsSaving(false);
    }
  };

  // Instagram Disconnect
  const handleDisconnectInstagram = async (session: Session) => {
    if (!window.confirm(`Tem certeza que deseja desconectar a conta do Instagram @${session.name}?`)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await logoutInstagramProxy(session.id);
      loadSessions();
    } catch (err: any) {
      setError(err.message || `Erro ao desconectar conta do Instagram: @${session.name}`);
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string | undefined) => {
    const s = status?.toLowerCase() || 'disconnected';
    if (s === 'connected') {
      return (
        <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          Conectado
        </span>
      );
    }
    if (s === 'qr' || s === 'connecting') {
      return (
        <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
          Aguardando QR Code
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-zinc-100 text-zinc-500 border border-zinc-200">
        Inativo
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-zinc-800 tracking-tight flex items-center gap-2">
            <Wifi className="w-7 h-7 text-purple-600 animate-pulse" />
            Canais & Conexões
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Gerencie suas instâncias de WhatsApp e contas de Instagram utilizadas para disparos automáticos e conversação.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setIsIgModalOpen(true)}
            className="flex items-center justify-center gap-2 text-xs font-bold text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-50 px-4 py-2.5 rounded-xl shadow-sm transition-all cursor-pointer"
          >
            <Instagram className="w-4 h-4 text-pink-600" />
            Instagram
          </button>
          <button
            onClick={() => setIsWaModalOpen(true)}
            className="flex items-center justify-center gap-2 text-xs font-bold text-white bg-gradient-to-r from-purple-700 to-indigo-600 hover:scale-[1.01] active:scale-[0.99] px-4 py-2.5 rounded-xl shadow-md cursor-pointer transition-all"
          >
            <Plus className="w-4 h-4" />
            WhatsApp
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-xs font-semibold">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}


      {/* Grid List or Error View */}
      {loading && sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] surface-card">
          <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
          <p className="text-sm text-zinc-400 mt-2 font-medium">Buscando conexões ativas...</p>
        </div>
      ) : error && sessions.length === 0 ? (
        <div className="surface-card p-8 bg-gradient-to-br from-rose-50/90 via-white/80 to-amber-50/50 border border-rose-200/80 shadow-lg relative overflow-hidden text-center flex flex-col items-center justify-center min-h-[280px]">
          <div className="w-16 h-16 rounded-2xl bg-rose-100/80 text-rose-600 flex items-center justify-center mb-4 shadow-inner ring-4 ring-rose-50">
            <WifiOff className="w-8 h-8 animate-bounce" />
          </div>
          
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-100/80 text-rose-700 text-[10px] font-black uppercase tracking-wider mb-2 border border-rose-200">
            <ShieldAlert className="w-3.5 h-3.5" />
            Serviço de Comunicação Inativo
          </div>

          <h3 className="text-lg font-black text-zinc-800 tracking-tight">
            Não foi possível carregar as conexões
          </h3>

          <p className="text-xs text-rose-700/90 font-medium mt-1.5 max-w-md  p-3 rounded-xl border border-rose-100 font-mono">
            {error}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 mt-5">
            <button
              onClick={loadSessions}
              className="flex items-center gap-2 text-xs font-bold text-zinc-700 bg-white hover:bg-zinc-50 border border-zinc-200 px-4 py-2.5 rounded-xl shadow-sm transition-all cursor-pointer hover:scale-105 active:scale-95"
            >
              <Loader2 className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Tentar Novamente
            </button>

            
          </div>
        </div>
      ) : sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[260px] surface-card text-center p-6 border-dashed border-2 border-zinc-200">
          <div className="w-16 h-16 rounded-full bg-purple-50 flex items-center justify-center text-purple-400 mb-4">
            <MessageSquare className="w-8 h-8" />
          </div>
          <h3 className="text-base font-bold text-zinc-700">Nenhum canal ativo</h3>
          <p className="text-xs text-zinc-400 mt-1 max-w-sm">
            Você ainda não conectou nenhum dispositivo. Crie uma conexão do WhatsApp para enviar e receber mensagens de seus leads.
          </p>
          <button
            onClick={() => setIsWaModalOpen(true)}
            className="mt-4 flex items-center gap-2 text-xs font-bold text-white bg-gradient-to-r from-purple-700 to-indigo-600 px-4 py-2 rounded-xl shadow-sm cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Criar Conexão
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map((session) => {
            const isWa = session.platform === 'whatsapp' || !session.platform;
            const status = extractStatus(session);
            
            return (
              <div key={session.id} className="surface-card p-6  border border-zinc-200/30 flex flex-col justify-between hover:shadow-lg transition-shadow relative overflow-hidden group">
                {/* Platform Indicator Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-sm ${
                      isWa ? 'bg-emerald-50 text-emerald-600' : 'bg-pink-50 text-pink-600'
                    }`}>
                      {isWa ? <MessageSquare className="w-5 h-5" /> : <Instagram className="w-5 h-5" />}
                    </div>
                    <div>
                      <h4 className="font-bold text-zinc-800 text-sm">{session.name}</h4>
                      <p className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
                        {isWa ? 'WhatsApp' : 'Instagram'}
                      </p>
                    </div>
                  </div>
                  {getStatusBadge(status)}
                </div>

                {/* Info and stats if available */}
                <div className="space-y-2.5 py-4 border-t border-zinc-100 flex-1">
                  <div className="flex justify-between text-xs font-medium text-zinc-500">
                    <span>ID da Instância:</span>
                    <span className="font-mono text-zinc-700 font-bold">{session.id}</span>
                  </div>
                  {isWa && session.stats && (
                    <div className="grid grid-cols-3 gap-2 pt-2 text-center  rounded-xl p-2.5 border border-zinc-100">
                      <div>
                        <div className="text-xs font-black text-zinc-800">{session.stats.conversationCount}</div>
                        <div className="text-[9px] uppercase font-bold text-zinc-400">Chats</div>
                      </div>
                      <div>
                        <div className="text-xs font-black text-zinc-800">{session.stats.messageCount}</div>
                        <div className="text-[9px] uppercase font-bold text-zinc-400">Mensagens</div>
                      </div>
                      <div>
                        <div className="text-xs font-black text-purple-600">{session.stats.unreadCount}</div>
                        <div className="text-[9px] uppercase font-bold text-zinc-400">Não lidas</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions footer */}
                <div className="flex items-center gap-2 pt-4 border-t border-zinc-100 mt-2">
                  {isWa && status !== 'connected' && (
                    <button
                      onClick={() => handleConnectWa(session)}
                      className="flex-1 flex items-center justify-center gap-1 text-[11px] font-extrabold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200/50 py-2 rounded-lg cursor-pointer transition-colors"
                    >
                      <QrCode className="w-3.5 h-3.5" />
                      Parear QR Code
                    </button>
                  )}

                  {isWa && status === 'connected' && (
                    <button
                      onClick={() => handleDisconnectWa(session)}
                      className="flex-1 flex items-center justify-center gap-1 text-[11px] font-extrabold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200/50 py-2 rounded-lg cursor-pointer transition-colors"
                    >
                      <WifiOff className="w-3.5 h-3.5" />
                      Desconectar
                    </button>
                  )}

                  {!isWa && (
                    <button
                      onClick={() => handleDisconnectInstagram(session)}
                      className="flex-1 flex items-center justify-center gap-1 text-[11px] font-extrabold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200/50 py-2 rounded-lg cursor-pointer transition-colors"
                    >
                      <LogOutInstagram />
                    </button>
                  )}

                  {isWa && (
                    <button
                      onClick={() => handleOpenSettings(session)}
                      className="p-2 text-zinc-400 hover:text-purple-600 bg-zinc-100 hover:bg-purple-50 border border-zinc-200/50 hover:border-zinc-200 rounded-lg cursor-pointer transition-all"
                      title="Configurações de Webhook"
                    >
                      <Settings className="w-3.5 h-3.5" />
                    </button>
                  )}

                  <button
                    onClick={() => isWa ? handleDeleteWa(session) : handleDisconnectInstagram(session)}
                    className="p-2 text-zinc-400 hover:text-rose-600 bg-zinc-100 hover:bg-rose-50 border border-zinc-200/50 hover:border-rose-100 rounded-lg cursor-pointer transition-all"
                    title="Excluir Conexão"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal WhatsApp Session Creation */}
      {isWaModalOpen && (
        <div className="fixed inset-0 z-50   flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-zinc-100 animate-[fade-in_0.2s_ease-out]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-zinc-800">Nova Conexão WhatsApp</h3>
              <button onClick={() => setIsWaModalOpen(false)} className="text-zinc-400 hover:text-zinc-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateWaSession} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Nome da Conexão</label>
                <input
                  type="text"
                  placeholder="ex: WhatsApp Comercial, Suporte"
                  className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2.5  focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  value={waSessionName}
                  onChange={(e) => setWaSessionName(e.target.value)}
                  disabled={waCreating}
                  required
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsWaModalOpen(false)}
                  className="px-4 py-2 border border-zinc-200 text-zinc-600 rounded-xl text-xs font-bold hover:bg-zinc-50 cursor-pointer"
                  disabled={waCreating}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-purple-700 to-indigo-600 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm cursor-pointer disabled:opacity-50"
                  disabled={waCreating}
                >
                  {waCreating && <Loader2 className="w-3 h-3 animate-spin" />}
                  Criar e Conectar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Instagram Connection */}
      {isIgModalOpen && (
        <div className="fixed inset-0 z-50   flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-zinc-100 animate-[fade-in_0.2s_ease-out]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-zinc-800">Conectar Instagram</h3>
              <button onClick={() => setIsIgModalOpen(false)} className="text-zinc-400 hover:text-zinc-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleInstagramLogin} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Usuário (Username)</label>
                <input
                  type="text"
                  placeholder="ex: dominuslabs"
                  className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2.5  focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  value={igUsername}
                  onChange={(e) => setIgUsername(e.target.value)}
                  disabled={igLoggingIn}
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Senha</label>
                <input
                  type="password"
                  placeholder="Senha do Instagram"
                  className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2.5  focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                  value={igPassword}
                  onChange={(e) => setIgPassword(e.target.value)}
                  disabled={igLoggingIn}
                  required
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsIgModalOpen(false)}
                  className="px-4 py-2 border border-zinc-200 text-zinc-600 rounded-xl text-xs font-bold hover:bg-zinc-50 cursor-pointer"
                  disabled={igLoggingIn}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-purple-700 to-indigo-600 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm cursor-pointer disabled:opacity-50"
                  disabled={igLoggingIn}
                >
                  {igLoggingIn && <Loader2 className="w-3 h-3 animate-spin" />}
                  Conectar Conta
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal QR Code Pairing (WhatsApp) */}
      {pairingSession && (
        <div className="fixed inset-0 z-50   flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-8 shadow-2xl border border-zinc-100 animate-[fade-in_0.2s_ease-out] text-center relative overflow-hidden">
            <button 
              onClick={() => {
                setPollingActive(false);
                setPairingSession(null);
              }} 
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-600 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-bold text-zinc-800 mb-1">Pareamento do WhatsApp</h3>
            <p className="text-xs text-zinc-500 mb-6">Escaneie o código QR usando o WhatsApp do celular para conectar.</p>

            {pairingStatus === 'connecting' && (
              <div className="flex flex-col items-center justify-center min-h-[220px]">
                <Loader2 className="w-10 h-10 text-purple-600 animate-spin" />
                <p className="text-xs text-zinc-400 mt-3 font-semibold animate-pulse">Solicitando canal com o servidor...</p>
              </div>
            )}

            {pairingStatus === 'connected' && (
              <div className="flex flex-col items-center justify-center min-h-[220px] text-emerald-600 animate-[bounce_1s_ease-in-out]">
                <CheckCircle2 className="w-16 h-16 mb-4" />
                <h4 className="font-extrabold text-sm">Dispositivo Conectado!</h4>
                <p className="text-[11px] text-zinc-400 mt-1">Sincronizando conversas, por favor aguarde...</p>
              </div>
            )}

            {pairingStatus === 'qr' && qrCodeUrl ? (
              <div className="flex flex-col items-center justify-center space-y-4">
                <div className="p-3 bg-white border border-zinc-100 rounded-2xl shadow-inner relative group">
                  <img src={qrCodeUrl} alt="QR Code WhatsApp" className="w-[180px] h-[180px] object-contain rounded-lg" />
                </div>
                <div className="text-[10px] text-purple-600 font-bold uppercase tracking-wider animate-pulse flex items-center gap-1.5 justify-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-ping"></span>
                  Aguardando leitura do celular...
                </div>
              </div>
            ) : (
              pairingStatus !== 'connecting' && pairingStatus !== 'connected' && (
                <div className="flex flex-col items-center justify-center min-h-[220px] text-zinc-400">
                  <ShieldAlert className="w-12 h-12 text-amber-500 mb-3" />
                  <h4 className="font-bold text-xs text-zinc-700">QR Code Temporariamente Indisponível</h4>
                  <p className="text-[10px] mt-1 max-w-[200px] leading-relaxed">
                    Estamos gerando as chaves. Se demorar, feche este modal e tente parear novamente.
                  </p>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Modal WhatsApp Session Settings */}
      {isSettingsModalOpen && settingsSession && (
        <div className="fixed inset-0 z-50   flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-xl border border-zinc-100 animate-[fade-in_0.2s_ease-out] max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-100">
              <div>
                <h3 className="text-base font-bold text-zinc-800">Configurações de Webhook</h3>
                <p className="text-xs text-zinc-400 font-medium">Sessão: {settingsSession.name}</p>
              </div>
              <button 
                onClick={() => {
                  setIsSettingsModalOpen(false);
                  setSettingsSession(null);
                }} 
                className="text-zinc-400 hover:text-zinc-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {settingsLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
                <p className="text-xs text-zinc-400 mt-2 font-medium">Buscando configurações...</p>
              </div>
            ) : (
              <form onSubmit={handleSaveSettings} className="space-y-4">
                {/* Enabled Toggle */}
                <div className="flex items-center justify-between p-3  border border-zinc-100 rounded-xl">
                  <div>
                    <label className="text-xs font-bold text-zinc-700">Ativar Webhook</label>
                    <p className="text-[10px] text-zinc-400">Envia notificações de mensagens recebidas para a URL configurada.</p>
                  </div>
                  <input
                    type="checkbox"
                    className="w-4.5 h-4.5 accent-purple-600 rounded cursor-pointer"
                    checked={webhookEnabled}
                    onChange={(e) => setWebhookEnabled(e.target.checked)}
                  />
                </div>

                {/* URL Input */}
                <div className="space-y-1">
                  <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">URL do Webhook</label>
                  <input
                    type="url"
                    placeholder="https://seu-crm.com/webhook-whatsapp"
                    className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2.5  focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    required={webhookEnabled}
                  />
                </div>

                {/* Secret Input */}
                <div className="space-y-1">
                  <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Chave Secreta (Secret - Opcional)</label>
                  <input
                    type="text"
                    placeholder="Assinatura secreta para validação no CRM"
                    className="w-full text-sm border border-zinc-200 rounded-xl px-3.5 py-2.5  focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                  />
                </div>

                {/* Event Permissions Checklist */}
                <div className="space-y-2 pt-2">
                  <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider block">Filtros de Eventos</label>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-zinc-100 hover:bg-zinc-50 cursor-pointer text-xs font-medium text-zinc-700">
                      <input
                        type="checkbox"
                        className="accent-purple-600 rounded"
                        checked={allowPrivate}
                        onChange={(e) => setAllowPrivate(e.target.checked)}
                      />
                      <span>Conversas Privadas (1-para-1)</span>
                    </label>

                    <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-zinc-100 hover:bg-zinc-50 cursor-pointer text-xs font-medium text-zinc-700">
                      <input
                        type="checkbox"
                        className="accent-purple-600 rounded"
                        checked={allowGroups}
                        onChange={(e) => setAllowGroups(e.target.checked)}
                      />
                      <span>Grupos</span>
                    </label>

                    <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-zinc-100 hover:bg-zinc-50 cursor-pointer text-xs font-medium text-zinc-700">
                      <input
                        type="checkbox"
                        className="accent-purple-600 rounded"
                        checked={allowNewsletters}
                        onChange={(e) => setAllowNewsletters(e.target.checked)}
                      />
                      <span>Canais/Newsletters</span>
                    </label>

                    <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-zinc-100 hover:bg-zinc-50 cursor-pointer text-xs font-medium text-zinc-700">
                      <input
                        type="checkbox"
                        className="accent-purple-600 rounded"
                        checked={allowBroadcasts}
                        onChange={(e) => setAllowBroadcasts(e.target.checked)}
                      />
                      <span>Listas de Transmissão</span>
                    </label>
                  </div>

                  <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-zinc-100 hover:bg-zinc-50 cursor-pointer text-xs font-medium text-zinc-700 mt-2 bg-purple-50/20 border-zinc-200/30">
                    <input
                      type="checkbox"
                      className="accent-purple-600 rounded"
                      checked={includeFromMe}
                      onChange={(e) => setIncludeFromMe(e.target.checked)}
                    />
                    <div>
                      <span className="font-bold">Incluir minhas próprias mensagens</span>
                      <p className="text-[9px] text-zinc-400 font-normal mt-0.5">Envia mensagens que você envia a partir do celular.</p>
                    </div>
                  </label>
                </div>

                <div className="flex justify-end gap-2 pt-4 border-t border-zinc-100 mt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setIsSettingsModalOpen(false);
                      setSettingsSession(null);
                    }}
                    className="px-4 py-2 border border-zinc-200 text-zinc-600 rounded-xl text-xs font-bold hover:bg-zinc-50 cursor-pointer"
                    disabled={settingsSaving}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-gradient-to-r from-purple-700 to-indigo-600 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm cursor-pointer disabled:opacity-50"
                    disabled={settingsSaving}
                  >
                    {settingsSaving && <Loader2 className="w-3 h-3 animate-spin" />}
                    Salvar Configurações
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Subcomponent to format Instagram Logout text
function LogOutInstagram() {
  return (
    <>
      <WifiOff className="w-3.5 h-3.5" />
      Sair do Instagram
    </>
  );
}

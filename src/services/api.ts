import { toast } from 'sonner';
export const getDynamicApiUrl = () => {
  const hostname = window.location.hostname;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return `${window.location.protocol}//${hostname}:8001/api/v1`;
  }
  // If we are accessing via ngrok, the proxy handles '/api' on the same port
  if (hostname.endsWith(".ngrok-free.dev") || hostname.endsWith(".ngrok.io")) {
    return `${window.location.protocol}//${hostname}/api/v1`;
  }
  // In a single-container deployment, the frontend is served by the backend.
  // We can just use the same domain/port dynamically.
  return `${window.location.protocol}//${hostname}/api/v1`;
};

export const API_BASE = import.meta.env.VITE_API_URL || getDynamicApiUrl();

function getHeaders(contentType: string | null = "application/json") {
  const headers: Record<string, string> = {};
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  const token = localStorage.getItem("admin_token");
  if (token && token !== "null" && token !== "undefined") {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// Mutex para deduplicar chamadas concorrentes de refresh de token
let activeRefreshPromise: Promise<string | null> | null = null;
let preventiveTimerId: any = null;

export function decodeJwtExp(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.exp || null;
  } catch (e) {
    return null;
  }
}

export function handleExpiredSessionRedirect() {
  localStorage.removeItem("admin_token");
  localStorage.removeItem("admin_refresh_token");
  localStorage.removeItem("whatsapp_token");
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

/**
 * Realiza a renovação silenciosa do access_token usando o refresh_token por baixo dos panos.
 * Deduplica requisições concorrentes através de activeRefreshPromise.
 */
export async function refreshAuthTokenSilently(): Promise<string | null> {
  if (activeRefreshPromise) {
    return activeRefreshPromise;
  }

  const refreshToken = localStorage.getItem("admin_refresh_token");
  if (!refreshToken || refreshToken === "null" || refreshToken === "undefined") {
    return null;
  }

  activeRefreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data && data.access_token) {
          localStorage.setItem("admin_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("admin_refresh_token", data.refresh_token);
          }
          if (data.whatsapp_token) {
            localStorage.setItem("whatsapp_token", data.whatsapp_token);
          }
          console.log("[SILENT-REAUTH] ✅ Token renovado com sucesso por baixo dos panos!");
          window.dispatchEvent(new CustomEvent("token_refreshed", { detail: { token: data.access_token } }));
          schedulePreventiveTokenRefresh();
          return data.access_token;
        }
      } else if (res.status === 401 || res.status === 403) {
        // O refresh_token expirou de fato ou foi revogado (após os 7 dias de validade)
        console.warn("[SILENT-REAUTH] ⚠️ Refresh token expirado ou inválido. Sessão encerrada.");
        handleExpiredSessionRedirect();
      }
    } catch (err) {
      console.warn("[SILENT-REAUTH] Falha de rede temporária ao renovar token:", err);
    } finally {
      activeRefreshPromise = null;
    }
    return null;
  })();

  return activeRefreshPromise;
}

// Alias para compatibilidade retroativa
export const refreshAuthTokenPreventively = refreshAuthTokenSilently;

export function getStoredAccessToken(): string | null {
  const token = localStorage.getItem("admin_token");
  if (!token || token === "null" || token === "undefined") return null;
  return token;
}

export function isTokenExpired(token: string, marginSec = 30): boolean {
  const exp = decodeJwtExp(token);
  if (!exp) return false; // Tokens sem exp (ex: testes) não são considerados expirados
  return Math.floor(Date.now() / 1000) >= exp - marginSec;
}

/**
 * Retorna um access_token garantidamente válido.
 * Se o token atual estiver expirado ou prestes a expirar nos próximos 30s,
 * renova silenciosamente usando o refresh_token antes de retornar.
 */
export async function getValidAccessToken(): Promise<string | null> {
  const token = getStoredAccessToken();
  const refreshToken = localStorage.getItem("admin_refresh_token");

  // Se já temos token e ele NÃO está expirado, retorna diretamente
  if (token && !isTokenExpired(token)) {
    return token;
  }

  // Se o token estiver expirado ou ausente, mas temos refresh token, renova por baixo dos panos
  if (refreshToken && refreshToken !== "null" && refreshToken !== "undefined") {
    const newToken = await refreshAuthTokenSilently();
    if (newToken) return newToken;
  }

  return token || null;
}

export function schedulePreventiveTokenRefresh() {
  if (preventiveTimerId) {
    clearTimeout(preventiveTimerId);
    preventiveTimerId = null;
  }

  const token = localStorage.getItem("admin_token");
  if (!token || token === "null" || token === "undefined") return;

  const exp = decodeJwtExp(token);
  if (!exp) return;

  const nowInSeconds = Math.floor(Date.now() / 1000);
  const secondsRemaining = exp - nowInSeconds;

  if (secondsRemaining <= 0) {
    refreshAuthTokenSilently();
    return;
  }

  // Agenda disparo preventivo 60s antes do token expirar
  const leadTimeSeconds = 60;
  const targetDelaySec = Math.max(secondsRemaining - leadTimeSeconds, 1);
  const delayMs = targetDelaySec * 1000;

  preventiveTimerId = setTimeout(() => {
    refreshAuthTokenSilently();
  }, delayMs);
}

// Executa o agendador preventivo ao carregar o arquivo de API
if (typeof window !== "undefined") {
  schedulePreventiveTokenRefresh();
}

export async function fetchWithAuth(
  url: string,
  options: RequestInit = {},
  contentType: string | null = "application/json"
) {
  let token = await getValidAccessToken();
  if (!token) {
    handleExpiredSessionRedirect();
    throw new Error("Sessão expirada. Por favor, faça login novamente.");
  }

  const mergedHeaders = {
    ...getHeaders(contentType),
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  } as Record<string, string>;

  let response = await fetch(url, {
    ...options,
    headers: mergedHeaders,
  });

  // Se o backend ainda assim responder 401 (ex: revogação forçada), tenta renovar 1 vez
  if (response.status === 401) {
    const isSubServiceRoute = url.includes("/whatsapp/");
    const refreshedToken = await refreshAuthTokenSilently();
    if (refreshedToken) {
      mergedHeaders["Authorization"] = `Bearer ${refreshedToken}`;
      response = await fetch(url, {
        ...options,
        headers: mergedHeaders,
      });
      return response;
    }

    if (!isSubServiceRoute) {
      handleExpiredSessionRedirect();
      throw new Error("Sessão expirada. Por favor, faça login novamente.");
    }
  }

  return response;
}

export async function loginUser(username: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Erro de login");
  }
  const data = await res.json();
  if (data && data.access_token) {
    localStorage.setItem("admin_token", data.access_token);
    if (data.refresh_token) {
      localStorage.setItem("admin_refresh_token", data.refresh_token);
    }
    schedulePreventiveTokenRefresh();
  }
  return data;
}

export async function fetchProjects() {
  const res = await fetchWithAuth(`${API_BASE}/projects/`);
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function fetchProject(id: string | number) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${id}`);
  if (!res.ok) throw new Error("Failed to fetch project");
  return res.json();
}

export async function createProject(data: any) {
  const res = await fetchWithAuth(`${API_BASE}/projects/`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function updateProject(id: string | number, data: any) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update project");
  return res.json();
}

export async function deleteProject(id: string | number) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to delete project");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Configurações Gerais da Empresa
// ---------------------------------------------------------------------------

export interface MenuItem {
  id?: string;
  name: string;
  category?: string;
  price?: number;
  description?: string;
  available?: boolean;
  stock?: number;
  image_url?: string;
}

export interface Promotion {
  id?: string;
  name: string;
  discount_type: 'percentage' | 'fixed' | 'free_shipping';
  discount_value: number;
  valid_until?: string;
  description?: string;
  active: boolean;
}

export interface CompanySettings {
  id?: number;
  tenant_id?: string;
  company_name?: string;
  niche?: string;
  cnpj_cpf?: string;
  phone?: string;
  email?: string;
  address?: string;
  address_number?: string;
  address_neighborhood?: string;
  address_city?: string;
  address_state?: string;
  address_zip?: string;
  business_hours?: string;
  tone_of_voice?: string;
  custom_instructions?: string;
  exchange_policy?: string;
  delivery_policy?: string;
  terms_of_service?: string;
  
  promotions?: Promotion[];
  accepted_payment_types?: string[];
  payment_notes?: string;
  values_mission?: string;
  additional_notes?: string;
  created_at?: string;
  updated_at?: string;
  delivery_fee_type?: string;
  delivery_fee_value?: number;
  delivery_radius_km?: number;
  delivery_max_coverage_km?: number;
  delivery_tiers?: { up_to_km: number; price: number }[];
  minimum_order_value?: number;
  preparation_time_minutes?: number;
}

export async function uploadProductMedia(file: File, productId: string, tenantId: string = "default") {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("product_id", productId);
  formData.append("tenant_id", tenantId);

  const token = localStorage.getItem("admin_token");
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/product-media/`, {
    method: "POST",
    headers, // Do NOT set Content-Type for FormData
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Falha ao enviar mídia do produto.");
  }
  return res.json();
}

export async function fetchCompanySettings(tenantId: string = "default"): Promise<CompanySettings> {
  const res = await fetchWithAuth(`${API_BASE}/company-settings/?tenant_id=${tenantId}`);
  if (!res.ok) throw new Error("Falha ao carregar configurações da empresa.");
  return res.json();
}

export async function updateCompanySettings(settings: CompanySettings, tenantId: string = "default"): Promise<CompanySettings> {
  const res = await fetchWithAuth(`${API_BASE}/company-settings/?tenant_id=${tenantId}`, {
    method: "PUT",
    body: JSON.stringify(settings),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao salvar configurações da empresa.");
  }
  return res.json();
}

export async function fetchPublicProject(publicToken: string) {
  // Public route - no auth headers needed
  const res = await fetch(`${API_BASE}/projects/public/${publicToken}`);
  if (!res.ok) throw new Error("Failed to fetch public project");
  return res.json();
}

export async function fetchTasks(projectId: string | number) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/tasks`);
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function createTask(projectId: string | number, data: any) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/tasks`, {
    method: "POST",
    body: JSON.stringify({ ...data, project_id: Number(projectId) }),
  });
  if (!res.ok) throw new Error("Failed to create task");
  return res.json();
}

export async function updateTask(taskId: string | number, data: any) {
  const res = await fetchWithAuth(`${API_BASE}/projects/tasks/${taskId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update task");
  return res.json();
}

export async function fetchAssets(projectId: string | number) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/assets`);
  if (!res.ok) throw new Error("Failed to fetch assets");
  return res.json();
}

export async function uploadAsset(projectId: string | number, file: File) {
  const formData = new FormData();
  formData.append("project_id", String(projectId));
  formData.append("file", file);

  const res = await fetchWithAuth(
    `${API_BASE}/uploads/`,
    {
      method: "POST",
      body: formData,
    },
    null // Empty Content-Type to let browser generate multipart boundaries
  );
  if (!res.ok) throw new Error("Failed to upload asset");
  return res.json();
}

export async function fetchCommits(projectId: string | number) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/commits`);
  if (!res.ok) throw new Error("Failed to fetch commits");
  return res.json();
}

export async function fetchDeploys(projectId: string | number) {
  const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/deploys`);
  if (!res.ok) throw new Error("Failed to fetch deploys");
  return res.json();
}

export async function submitFeedback(payload: {
  project_token: string;
  final_result: string;
  service_rating: string;
  invested_value_rating: string;
  process_rating: string;
  improvements: string;
  rating: number;
}) {
  const res = await fetch(`${API_BASE}/projects/public/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Falha ao enviar feedback.");
  }
  return res.json();
}

export async function fetchShowcaseData() {
  const res = await fetch(`${API_BASE}/projects/public/showcase/data`);
  if (!res.ok) throw new Error("Failed to fetch showcase data");
  return res.json();
}


export function getUserTenant(): string {
  const token = localStorage.getItem("admin_token");
  if (!token) return "default";
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return "default";
    const payload = JSON.parse(atob(parts[1]));
    return payload.tenant_id || "default";
  } catch (e) {
    return "default";
  }
}

export function getUserRole(): string {
  const token = localStorage.getItem("admin_token");
  if (!token) return "";
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return "";
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.role || "admin";
  } catch (e) {
    console.error("Failed to decode token", e); toast.error("Ocorreu um erro na operacao.");
    return "";
  }
}

export async function fetchWhatsappSessions() {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions`);
  if (!res.ok) throw new Error("Falha ao buscar conexões.");
  return res.json();
}

export async function createWhatsappSession(name: string) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions`, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao criar conexão.");
  }
  return res.json();
}

export async function connectWhatsappSession(sessionId: string) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions/${sessionId}/connect`, {
    method: "POST",
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao solicitar código QR.");
  }
  return res.json();
}

export async function getWhatsappSessionStatus(sessionId: string) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions/${sessionId}`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao consultar status da sessão.");
  }
  return res.json();
}

export async function getWhatsappSessionSettings(sessionId: string) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions/${sessionId}/settings`);
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao buscar configurações da sessão.");
  }
  return res.json();
}

export async function updateWhatsappSessionSettings(sessionId: string, settingsData: any) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions/${sessionId}/settings`, {
    method: "PUT",
    body: JSON.stringify(settingsData),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao atualizar configurações da sessão.");
  }
  return res.json();
}

export async function disconnectWhatsappSession(sessionId: string) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions/${sessionId}/disconnect`, {
    method: "POST",
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao desconectar sessão.");
  }
  return res.json();
}

export async function deleteWhatsappSession(sessionId: string) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao excluir sessão.");
  }
  return res.json();
}

export async function loginInstagramProxy(payload: { username: string; password: string }) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/instagram/login`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao conectar Instagram.");
  }
  return res.json();
}

export async function logoutInstagramProxy(username: string) {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/instagram/sessions/${username}/logout`, {
    method: "POST",
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao desconectar Instagram.");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Preferência de sessão WhatsApp
// ---------------------------------------------------------------------------

export async function fetchSessionPreference(): Promise<{ session_id: string | null }> {
  const res = await fetchWithAuth(`${API_BASE}/crm/preferences/session`);
  if (!res.ok) throw new Error("Falha ao buscar preferência de sessão.");
  return res.json();
}

export async function setSessionPreference(session_id: string): Promise<{ session_id: string; ok: boolean }> {
  const res = await fetchWithAuth(`${API_BASE}/crm/preferences/session`, {
    method: "PUT",
    body: JSON.stringify({ session_id }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao salvar preferência de sessão.");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Envio de mensagem com sessão
// ---------------------------------------------------------------------------

export async function sendWhatsappMessage(payload: {
  lead_id: string;
  phone: string;
  message: string;
  session_id?: string;
}) {
  const res = await fetchWithAuth(`${API_BASE}/crm/messages/send`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao enviar mensagem.");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Credenciais manuais da WhatsApp API (client_id + client_secret)
// ---------------------------------------------------------------------------

export async function fetchCredentials(): Promise<{
  configured: boolean;
  client_id: string | null;
  client_secret_preview: string | null;
  created_at: string | null;
}> {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/credentials`);
  if (!res.ok) throw new Error("Falha ao buscar credenciais.");
  return res.json();
}

export async function saveCredentials(client_id: string, client_secret: string): Promise<{
  ok: boolean;
  client_id: string;
  client_secret_preview: string;
  message: string;
}> {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/credentials`, {
    method: "PUT",
    body: JSON.stringify({ client_id, client_secret }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao salvar credenciais.");
  }
  return res.json();
}

export async function provisionCredentials(): Promise<{
  ok: boolean;
  client_id: string;
  client_secret: string;
  message: string;
}> {
  const res = await fetchWithAuth(`${API_BASE}/whatsapp/provision`, {
    method: "POST",
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao vincular com a WhatsApp API.");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Omnichannel API Actions (get_contacts, get_conversations, get_chat_history)
// ---------------------------------------------------------------------------

export async function fetchContacts() {
  const res = await fetchWithAuth(`${API_BASE}/crm/contacts`);
  if (!res.ok) throw new Error("Falha ao carregar lista de contatos.");
  return res.json();
}

export async function fetchConversations() {
  const res = await fetchWithAuth(`${API_BASE}/crm/conversations`);
  if (!res.ok) throw new Error("Falha ao carregar lista de conversas.");
  return res.json();
}

export async function fetchChatHistory(contactJid: string, sessionId?: string) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  const res = await fetchWithAuth(`${API_BASE}/crm/chat-history/${encodeURIComponent(contactJid)}${query}`);
  if (!res.ok) throw new Error("Falha ao carregar histórico da conversa.");
  return res.json();
}

export async function sendOmnichannelMessage(payload: {
  contact_jid: string;
  session_id?: string;
  message: string;
  phone?: string;
}) {
  const res = await fetchWithAuth(`${API_BASE}/crm/messages/send`, {
    method: "POST",
    body: JSON.stringify({
      lead_id: payload.contact_jid,
      phone: payload.phone || payload.contact_jid,
      message: payload.message,
      session_id: payload.session_id,
    }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao enviar mensagem.");
  }
  return res.json();
}

export async function sendOmnichannelMedia(payload: {
  contact_jid: string;
  session_id?: string;
  text?: string;
  media: {
    kind: 'image' | 'video' | 'audio' | 'document' | string;
    mimeType?: string;
    fileName?: string;
    data: string;
  };
}) {
  const res = await fetchWithAuth(`${API_BASE}/crm/messages/send-media`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Falha ao enviar arquivo de mídia.");
  }
  return res.json();
}



// ---------------------------------------------------------------------------
// Produtos / Cardápio
// ---------------------------------------------------------------------------

export const fetchProducts = async (tenantId: string = 'default'): Promise<MenuItem[]> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products`, {
    headers,
  });
  if (!response.ok) throw new Error('Erro ao buscar produtos');
  return response.json();
};

export const createProduct = async (product: MenuItem, tenantId: string = 'default'): Promise<MenuItem> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products`, {
    method: 'POST',
    headers,
    body: JSON.stringify(product),
  });
  if (!response.ok) throw new Error('Erro ao criar produto');
  return response.json();
};

export const updateProduct = async (id: string, product: MenuItem, tenantId: string = 'default'): Promise<MenuItem> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products/${id}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(product),
  });
  if (!response.ok) throw new Error('Erro ao atualizar produto');
  return response.json();
};

export const deleteProduct = async (id: string, tenantId: string = 'default'): Promise<void> => {
  const headers = getHeaders();
  headers['x-tenant-id'] = tenantId;
  const response = await fetch(`${API_BASE}/products/${id}`, {
    method: 'DELETE',
    headers,
  });
  if (!response.ok) throw new Error('Erro ao deletar produto');
};


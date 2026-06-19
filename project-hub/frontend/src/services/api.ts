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

export async function fetchWithAuth(
  url: string,
  options: RequestInit = {},
  contentType: string | null = "application/json"
) {
  const token = localStorage.getItem("admin_token");
  if (!token || token === "null" || token === "undefined") {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_refresh_token");
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Sessão expirada. Por favor, faça login novamente.");
  }

  const mergedHeaders = {
    ...getHeaders(contentType),
    ...(options.headers || {}),
  } as Record<string, string>;

  // Ensure authorization header is set correctly
  mergedHeaders["Authorization"] = `Bearer ${token}`;

  let response = await fetch(url, {
    ...options,
    headers: mergedHeaders,
  });

  if (response.status === 401) {
    const refreshToken = localStorage.getItem("admin_refresh_token");
    if (refreshToken && refreshToken !== "null" && refreshToken !== "undefined") {
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          if (refreshData && refreshData.access_token) {
            localStorage.setItem("admin_token", refreshData.access_token);
            if (refreshData.refresh_token) {
              localStorage.setItem("admin_refresh_token", refreshData.refresh_token);
            }
            if (refreshData.whatsapp_token) {
              localStorage.setItem("whatsapp_token", refreshData.whatsapp_token);
            }

            // Retry the original request with the new token
            mergedHeaders["Authorization"] = `Bearer ${refreshData.access_token}`;
            response = await fetch(url, {
              ...options,
              headers: mergedHeaders,
            });

            if (response.status !== 401) {
              return response;
            }
          }
        }
      } catch (err) {
        console.error("Token refresh failed:", err);
      }
    }

    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_refresh_token");
    localStorage.removeItem("whatsapp_token");
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Sessão expirada. Por favor, faça login novamente.");
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
  return res.json();
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

export function getUserRole(): string {
  const token = localStorage.getItem("admin_token");
  if (!token) return "";
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return "";
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.role || "admin";
  } catch (e) {
    console.error("Failed to decode token", e);
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


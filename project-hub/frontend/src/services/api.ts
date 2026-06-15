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

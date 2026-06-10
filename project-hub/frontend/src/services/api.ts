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
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
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
  const res = await fetch(`${API_BASE}/projects/`, {
    headers: getHeaders(),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function fetchProject(id: string | number) {
  const res = await fetch(`${API_BASE}/projects/${id}`, {
    headers: getHeaders(),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to fetch project");
  return res.json();
}

export async function createProject(data: any) {
  const res = await fetch(`${API_BASE}/projects/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function updateProject(id: string | number, data: any) {
  const res = await fetch(`${API_BASE}/projects/${id}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
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
  const res = await fetch(`${API_BASE}/projects/${projectId}/tasks`, {
    headers: getHeaders(),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function createTask(projectId: string | number, data: any) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/tasks`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ ...data, project_id: Number(projectId) }),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to create task");
  return res.json();
}

export async function updateTask(taskId: string | number, data: any) {
  const res = await fetch(`${API_BASE}/projects/tasks/${taskId}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to update task");
  return res.json();
}

export async function fetchAssets(projectId: string | number) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/assets`, {
    headers: getHeaders(),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to fetch assets");
  return res.json();
}

export async function uploadAsset(projectId: string | number, file: File) {
  const formData = new FormData();
  formData.append("project_id", String(projectId));
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/uploads/`, {
    method: "POST",
    headers: getHeaders(null), // Empty Content-Type to let browser generate multipart boundaries
    body: formData,
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to upload asset");
  return res.json();
}

export async function fetchCommits(projectId: string | number) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/commits`, {
    headers: getHeaders(),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to fetch commits");
  return res.json();
}

export async function fetchDeploys(projectId: string | number) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/deploys`, {
    headers: getHeaders(),
  });
  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
  }
  if (!res.ok) throw new Error("Failed to fetch deploys");
  return res.json();
}

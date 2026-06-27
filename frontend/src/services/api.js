const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// helpers

function authHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(method, path, { body, isFormData } = {}) {
  const headers = { ...authHeaders() };
  if (!isFormData) headers['Content-Type'] = 'application/json';

  const opts = { method, headers };
  if (body) {
    opts.body = isFormData ? body : JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const err = new Error(data.error || data.message || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }

  return data;
}

// Auth 

export async function register(email, username, password) {
  const data = await request('POST', '/api/auth/register', { body: { email, username, password } });
  return data;
}

export async function login(email, password) {
  const data = await request('POST', '/api/auth/login', { body: { email, password } });
  return data;
}

export async function getMe() {
  const data = await request('GET', '/api/auth/me');
  return data;
}

export async function logout() {
  const data = await request('POST', '/api/auth/logout');
  return data;
}

// Projects

export async function createProject(projectName, description) {
  const data = await request('POST', '/api/projects', { body: { project_name: projectName, description } });
  return data;
}

export async function getProjects(page = 1, perPage = 20) {
  const data = await request('GET', `/api/projects?page=${page}&per_page=${perPage}`);
  return data;
}

export async function getProject(id) {
  const data = await request('GET', `/api/projects/${id}`);
  return data;
}

export async function updateProject(id, updates) {
  const data = await request('PATCH', `/api/projects/${id}`, { body: updates });
  return data;
}

export async function deleteProject(id) {
  const data = await request('DELETE', `/api/projects/${id}`);
  return data;
}

//  Documents 

export async function uploadFiles(files, projectId) {
  const formData = new FormData();
  files.forEach((f) => formData.append('files[]', f));
  if (projectId) formData.append('project_id', projectId);
  const data = await request('POST', '/api/documents/upload', { body: formData, isFormData: true });
  return data;
}

export async function getDocuments(projectId) {
  const path = projectId ? `/api/documents?project_id=${projectId}` : '/api/documents';
  const data = await request('GET', path);
  return data;
}

export async function getDocumentsPreview() {
  const data = await request('GET', '/api/documents/preview');
  return data;
}

export async function getDocument(id) {
  const data = await request('GET', `/api/documents/${id}`);
  return data;
}

export async function deleteDocument(id) {
  const data = await request('DELETE', `/api/documents/${id}`);
  return data;
}

export async function getDocumentText(id) {
  const data = await request('GET', `/api/documents/${id}/text`);
  return data;
}

export async function getDocumentThumbnailUrl(id) {
  const data = await request('GET', `/api/documents/${id}/thumbnail`)
  return data.url
}

export async function getDocumentContentUrl(id) {
  const data = await request('GET', `/api/documents/${id}/content`)
  return data.url
}

//  Chat / Conversations 
// export async function sendChatMessage(query, projectId, conversationId = null, topK = 5) {
//   const body = { query, top_k: topK };
//   if (projectId) body.project_id = projectId;
//   if (conversationId) body.conversation_id = conversationId;
//   const data = await request('POST', '/api/chats/answer', { body });
//   return data;
// }

// SSE stream support
export async function sendChatMessage(
  query,
  projectId,
  conversationId = null,
  topK = 5,
  onNewConversation, // callback: (meta: { conversation_id, title }) => void
  onToken,        // callback: (token: string) => void
  onDone,         // callback: (meta: { conversation_id, is_new_conversation, ... }) => void
  onError,        // callback: (message: string) => void
) {
  const body = { query, top_k: topK };
  if (projectId) body.project_id = projectId;
  if (conversationId) body.conversation_id = conversationId;

  const response = await fetch(`${API_BASE}/api/chats/answer/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${localStorage.getItem('access_token')}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    onError?.(err.message || "Request failed");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();   // hold incomplete line for next chunk

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;

      let event;
      try {
        event = JSON.parse(line.slice(6));
      } catch {
        continue;
      }

      if (event.type === "token") onToken?.(event.content);
      else if (event.type === "new_conversation") onNewConversation?.(event);
      else if (event.type === "done") onDone?.(event);
      else if (event.type === "error") onError?.(event.message);
    }
  }
}

export async function getConversations(projectId, page = 1) {
  const path = projectId ? `/api/conversations/?project_id=${projectId}&page=${page}` : `/api/conversations/?page=${page}`;
  const data = await request('GET', path);
  return data;
}

export async function getConversation(conversationId) {
  const data = await request('GET', `/api/conversations/${conversationId}`);
  return data;
}

export async function deleteConversation(conversationId) {
  const data = await request('DELETE', `/api/conversations/${conversationId}`);
  return data;
}

export async function deleteDocuments(documentIds) {
  const data = await request('POST', '/api/documents/delete', { body: { document_ids: documentIds } });
  return data;
}


const BASE_URL = "http://13.62.54.109/api";

//   Token store  
let _accessToken  = null;
let _refreshToken = null;

export function setTokens(access, refresh) {
  _accessToken  = access;
  _refreshToken = refresh;
  if (access)  sessionStorage.setItem("bm_at", access);
  if (refresh) sessionStorage.setItem("bm_rt", refresh);
}

export function clearTokens() {
  _accessToken  = null;
  _refreshToken = null;
  sessionStorage.removeItem("bm_at");
  sessionStorage.removeItem("bm_rt");
}

export function loadTokensFromSession() {
  _accessToken  = sessionStorage.getItem("bm_at");
  _refreshToken = sessionStorage.getItem("bm_rt");
  return !!_accessToken;
}

export function hasTokens() { return !!_accessToken; }


//   Core fetch wrapper with auto token refresh  
async function apiFetch(url, options = {}, retry = true) {
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  if (_accessToken) headers["Authorization"] = `Bearer ${_accessToken}`;

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401 && retry && _refreshToken) {
    const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ refresh_token: _refreshToken }),
    });
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      setTokens(data.access_token, data.refresh_token || _refreshToken);
      return apiFetch(url, options, false);
    } else {
      clearTokens();
      window.dispatchEvent(new Event("auth:logout"));
      throw new Error("Session expired. Please log in again.");
    }
  }
  return res;
}


//  Auth  

export async function register(email, username, password) {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ email, username, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Registration failed.");
  setTokens(data.access_token, data.refresh_token);
  return data.user;
}

export async function login(email, password) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed.");
  setTokens(data.access_token, data.refresh_token);
  return data.user;
}

export async function logout() { clearTokens(); }

export async function getMe() {
  if (!_accessToken) return null;
  try {
    const res = await apiFetch(`${BASE_URL}/auth/me`);
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}


//   Upload  
// Uses XMLHttpRequest for progress events.
// Manually attaches Bearer token since apiFetch only wraps fetch().

export async function uploadBook(file, onProgress) {
  // If token is expired, try to refresh BEFORE starting the upload
  // (XHR doesn't support our auto-refresh logic)
  if (_refreshToken) {
    try {
      const testRes = await apiFetch(`${BASE_URL}/auth/me`);
      if (!testRes.ok && testRes.status === 401) {
        throw new Error("Not authenticated");
      }
    } catch {
      throw new Error("Session expired. Please log in again.");
    }
  }

  const formData = new FormData();
  formData.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress)
        onProgress(Math.round((e.loaded / e.total) * 100));
    });

    xhr.addEventListener("load", () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status === 201) {
          resolve(data);
        } else {
          reject(new Error(data.detail || `Upload failed (${xhr.status})`));
        }
      } catch {
        reject(new Error(`Upload failed (${xhr.status}): ${xhr.responseText}`));
      }
    });

    xhr.addEventListener("error", () =>
      reject(new Error("Network error. Check if backend is running."))
    );

    xhr.addEventListener("timeout", () =>
      reject(new Error("Upload timed out. File may be too large."))
    );

    xhr.timeout = 300000; // 5 minute timeout for large PDFs
    xhr.open("POST", `${BASE_URL}/upload`);

    // Attach Bearer token — critical, without this → 401
    if (_accessToken) xhr.setRequestHeader("Authorization", `Bearer ${_accessToken}`);

    xhr.send(formData);
  });
}


//   Chats  

export async function createChat({ bookId, bookName, totalPages, totalChunks }) {
  const res = await apiFetch(`${BASE_URL}/chats`, {
    method: "POST",
    body: JSON.stringify({
      book_id: bookId, book_name: bookName,
      total_pages: totalPages, total_chunks: totalChunks,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to create chat");
  return data;
}

export async function getAllChats() {
  const res = await apiFetch(`${BASE_URL}/chats`);
  if (!res.ok) throw new Error("Failed to load chats");
  return res.json();
}

export async function getChatMessages(chatId) {
  const res = await apiFetch(`${BASE_URL}/chats/${chatId}/messages`);
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();
}

export async function deleteChat(chatId) {
  await apiFetch(`${BASE_URL}/chats/${chatId}`, { method: "DELETE" });
}

export async function generateQuiz(bookId, topic, numQuestions = 5) {
  const res = await apiFetch(`${BASE_URL}/quiz`, {
    method: "POST",
    body: JSON.stringify({ book_id: bookId, topic, num_questions: numQuestions }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to generate quiz");
  return data;
}


//   Streaming query  

export async function streamQuestion(bookId, question, chatId, callbacks) {
  const { onStatus, onToken, onSources, onDone, onError } = callbacks;

  let response;
  try {
    response = await fetch(`${BASE_URL}/query/stream`, {
      method:  "POST",
      headers: {
        "Content-Type":  "application/json",
        "Authorization": _accessToken ? `Bearer ${_accessToken}` : "",
      },
      body: JSON.stringify({ book_id: bookId, question, chat_id: chatId }),
    });
  } catch {
    onError?.("Network error. Is the backend running?");
    return;
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    onError?.(err.detail || `Request failed (${response.status})`);
    return;
  }

  const reader  = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer      = "";
  let tokenBuffer = "";
  let rafId       = null;
  let streamDone  = false;

  function flushTokens() {
    if (tokenBuffer) { onToken?.(tokenBuffer); tokenBuffer = ""; }
    if (!streamDone) rafId = requestAnimationFrame(flushTokens);
  }
  rafId = requestAnimationFrame(flushTokens);

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop();

      for (const event of events) {
        const line = event.trim();
        if (!line.startsWith("data: ")) continue;
        let payload;
        try { payload = JSON.parse(line.slice(6)); } catch { continue; }

        switch (payload.type) {
          case "status":  onStatus?.(payload.content); break;
          case "token":   tokenBuffer += payload.content; break;
          case "sources": onSources?.(payload.content); break;
          case "done":
            streamDone = true; cancelAnimationFrame(rafId);
            if (tokenBuffer) { onToken?.(tokenBuffer); tokenBuffer = ""; }
            onDone?.(); return;
          case "error":
            streamDone = true; cancelAnimationFrame(rafId);
            onError?.(payload.content); return;
        }
      }
    }
  } finally {
    streamDone = true; cancelAnimationFrame(rafId);
    if (tokenBuffer) { onToken?.(tokenBuffer); tokenBuffer = ""; }
    onDone?.();
  }
}
//  const BASE_URL = "http://localhost:8000/api";
const BASE_URL = import.meta.env.VITE_API_URL;
 
async function apiFetch(url, options = {}, retry = true) {
  const res = await fetch(url, {
    ...options,
    credentials: "include",   // sends cookies automatically
    headers: { "Content-Type": "application/json", ...options.headers },
  });

  if (res.status === 401 && retry) {
    // Try refreshing the access token using the refresh token cookie
    const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });

    if (refreshRes.ok) {
      // Got new access token cookie — retry original request
      return apiFetch(url, options, false);
    } else {
      // Refresh also failed — force logout
      window.dispatchEvent(new Event("auth:logout"));
      throw new Error("Session expired. Please log in again.");
    }
  }

  return res;
}


export async function register(email, username, password) {
  const res = await apiFetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Registration failed.");
  return data;   // { user_id, email, username }
}

export async function login(email, password) {
  const res = await apiFetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed.");
  return data;
}

export async function logout() {
  await apiFetch(`${BASE_URL}/auth/logout`, { method: "POST" });
}

export async function getMe() {
  // Called on app load to check if user is already logged in
  const res = await apiFetch(`${BASE_URL}/auth/me`);
  if (!res.ok) return null;
  return res.json();   // { user_id, email, username } or null
}


export async function uploadBook(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.withCredentials = true;   // send cookies with XHR too
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    });
    xhr.addEventListener("load", () => {
      const data = JSON.parse(xhr.responseText);
      xhr.status === 201 ? resolve(data) : reject(new Error(data.detail || "Upload failed"));
    });
    xhr.addEventListener("error", () => reject(new Error("Network error.")));
    xhr.open("POST", `${BASE_URL}/upload`);
    xhr.send(formData);
  });
}


export async function createChat({ bookId, bookName, totalPages, totalChunks }) {
  const res = await apiFetch(`${BASE_URL}/chats`, {
    method: "POST",
    body: JSON.stringify({ book_id: bookId, book_name: bookName, total_pages: totalPages, total_chunks: totalChunks }),
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


export async function streamQuestion(bookId, question, chatId, callbacks) {
  const { onStatus, onToken, onSources, onDone, onError } = callbacks;

  let response;
  try {
    response = await fetch(`${BASE_URL}/query/stream`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
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

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let tokenBuffer = "";
  let rafId = null;
  let streamDone = false;

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



export async function generateQuiz(bookId, topic, numQuestions = 5) {
  const res = await apiFetch(`${BASE_URL}/quiz`, {
    method: "POST",
    body: JSON.stringify({
      book_id:       bookId,
      topic,
      num_questions: numQuestions,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to generate quiz");
  return data;   // { questions: [...] }
}
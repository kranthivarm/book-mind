// services/api.js
const BASE_URL = "http://localhost:8000/api";

//   Upload  
export async function uploadBook(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
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

//  Chat CRUD (Postgres-backed)

export async function createChat({ bookId, bookName, totalPages, totalChunks }) {
  const res = await fetch(`${BASE_URL}/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      book_id: bookId, book_name: bookName,
      total_pages: totalPages, total_chunks: totalChunks,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to create chat");
  return data;  // { chat_id, book_id, book_name, ... }
}

export async function getAllChats() {
  const res = await fetch(`${BASE_URL}/chats`);
  if (!res.ok) throw new Error("Failed to load chats");
  return res.json();  // [{chat_id, book_name, last_message, ...}]
}

export async function getChatMessages(chatId) {
  const res = await fetch(`${BASE_URL}/chats/${chatId}/messages`);
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();  // [{message_id, role, text, sources, created_at}]
}

export async function deleteChat(chatId) {
  await fetch(`${BASE_URL}/chats/${chatId}`, { method: "DELETE" });
}

//   Streaming query 

export async function streamQuestion(bookId, question, chatId, callbacks) {
  const { onStatus, onToken, onSources, onDone, onError } = callbacks;

  let response;
  try {
    response = await fetch(`${BASE_URL}/query/stream`, {
      method: "POST",
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

  const reader  = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let   buffer  = "";
  let   tokenBuffer  = "";
  let   rafId        = null;
  let   streamDone   = false;

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
            streamDone = true;
            cancelAnimationFrame(rafId);
            if (tokenBuffer) { onToken?.(tokenBuffer); tokenBuffer = ""; }
            onDone?.();
            return;
          case "error":
            streamDone = true;
            cancelAnimationFrame(rafId);
            onError?.(payload.content);
            return;
        }
      }
    }
  } finally {
    streamDone = true;
    cancelAnimationFrame(rafId);
    if (tokenBuffer) { onToken?.(tokenBuffer); tokenBuffer = ""; }
    onDone?.();
  }
}
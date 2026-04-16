const BASE_URL = "http://localhost:8000/api";

/**
 * Uploads a PDF file to the backend.
 * Uses FormData because we're sending a binary file (multipart/form-data).
 * DO NOT set Content-Type header manually — browser sets it with boundary.
 *
 * @param {File} file - The PDF File object from the file input
 * @param {Function} onProgress - Optional callback(percent) for upload progress
 * @returns {Promise<{book_id, filename, total_pages, total_chunks, message}>}
 */
export async function uploadBook(file, onProgress) {
  const formData = new FormData();
  formData.append("file", file); // key "file" matches FastAPI's parameter name

  // Use XMLHttpRequest instead of fetch to get upload progress events
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track upload progress (0–100%)
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener("load", () => {
      const data = JSON.parse(xhr.responseText);
      if (xhr.status === 201) {
        resolve(data);
      } else {
        // Backend sends { detail: "..." } for errors
        reject(new Error(data.detail || "Upload failed"));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Network error. Is the backend running on port 8000?"));
    });

    xhr.open("POST", `${BASE_URL}/upload`);
    xhr.send(formData);
  });
}

/**
 * Sends a question to the RAG pipeline.
 
 * @param {string} bookId - The book_id returned by uploadBook
 * @param {string} question - The student's question
 * @returns {Promise<{answer, question, sources: [{page_number, chunk_index, text_preview, relevance_score}]}>}
 */
export async function askQuestion(bookId, question) {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ book_id: bookId, question }),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Failed to get answer");
  }

  return data;
}





//  Streaming query 
/**
 * Sends a question and reads the SSE stream from /query/stream.
 *
 * HOW SSE READING WORKS IN THE BROWSER:
 *   fetch() returns a Response whose body is a ReadableStream.
 *   We attach a TextDecoder and read the stream chunk by chunk.
 *   Each chunk may contain one or more SSE events separated by "\n\n".
 *   We split on "\n\n", parse each event's JSON, and call the right callback.
 *
 * @param {string}   bookId
 * @param {string}   question
 * @param {object}   callbacks
 *   callbacks.onStatus(message)    — "Searching textbook…" / "Generating…"
 *   callbacks.onToken(text)        — called for each token from the LLM
 *   callbacks.onSources(sources)   — called once with the final sources array
 *   callbacks.onDone()             — called when stream is complete
 *   callbacks.onError(message)     — called if something goes wrong
 */

export async function streamQuestion(bookId, question, callbacks) {
  const { onStatus, onToken, onSources, onDone, onError } = callbacks;
 
  let response;
  try {
    response = await fetch(`${BASE_URL}/query/stream`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ book_id: bookId, question }),
    });
  } catch (err) {
    onError?.("Network error. Is the backend running?");
    return;
  }
 
  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    onError?.(errData.detail || `Request failed (${response.status})`);
    return;
  }
 
  //   Read the stream  
  const reader  = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let   buffer  = "";   // accumulates partial chunks between reads
 
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
 
    // Decode the incoming bytes and add to buffer
    buffer += decoder.decode(value, { stream: true });
 
    // SSE events are separated by double newline "\n\n"
    // Split on it to get individual events
    const events = buffer.split("\n\n");
 
    // The last element may be a partial event (stream cut mid-event)
    // Keep it in the buffer for the next read
    buffer = events.pop();
 
    for (const event of events) {
      // Each SSE event looks like:  "data: {json}"
      // Strip the "data: " prefix, then parse JSON
      const line = event.trim();
      if (!line.startsWith("data: ")) continue;
 
      let payload;
      try {
        payload = JSON.parse(line.slice(6));  // slice off "data: "
      } catch {
        continue;  // malformed JSON — skip
      }
 
      // Route to the right callback based on event type
      switch (payload.type) {
        case "status":  onStatus?.(payload.content);  break;
        case "token":   onToken?.(payload.content);   break;
        case "sources": onSources?.(payload.content); break;
        case "done":    onDone?.();                   return;
        case "error":   onError?.(payload.content);   return;
      }
    }
  }
 
  // Stream ended without a "done" event (shouldn't happen, but handle it)
  onDone?.();
}
 
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
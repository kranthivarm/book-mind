import { useState, useRef, useCallback } from "react";
import { uploadBook } from "../services/api";
import "../styles/pages/Uploadpage.css";

export default function UploadPage({ onUploadSuccess }) {
  //   State 
  const [dragOver, setDragOver]     = useState(false);    // highlight drop zone
  const [file, setFile]             = useState(null);     // selected File object
  const [uploading, setUploading]   = useState(false);    // show spinner
  const [progress, setProgress]     = useState(0);        // 0–100 upload %
  const [error, setError]           = useState("");       // error message
  const [success, setSuccess]       = useState(null);     // upload response data

  const fileInputRef = useRef(null);

  //  File validation 
  const validateFile = (f) => {
    if (!f) return "No file selected.";
    if (f.type !== "application/pdf" && !f.name.endsWith(".pdf"))
      return "Only PDF files are supported.";
    // if (f.size > 50 * 1024 * 1024)
    if (f.size > 200 * 1024 * 1024)
      return "File is too large. Maximum size is 50MB.";
    return null; // null = no error
  };

  //  Handle file pick (from input or drop) 
  const handleFile = useCallback((f) => {
    setError("");
    setSuccess(null);
    const err = validateFile(f);
    if (err) { setError(err); return; }
    setFile(f);
  }, []);

  const onDragOver  = (e) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = ()  => setDragOver(false);
  const onDrop      = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    handleFile(dropped);
  };

  //  Upload handler
  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    setError("");

    try {
      // uploadBook sends multipart/form-data and calls onProgress with 0–100
      const data = await uploadBook(file, setProgress);
      setSuccess(data);

      // Wait 1.5s so student can see the success stats, then go to chat
      setTimeout(() => onUploadSuccess(data), 1500);
    } catch (err) {
      setError(err.message);
      setUploading(false);
    }
  };

  return (
    <div className="upload-page">
      {/* Decorative background blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />

      <div className="upload-container fade-up">

        {/* Header */}
        <header className="upload-header">
          <div className="logo-mark">📖</div>
          <h1 className="upload-title">PdfChat</h1>
          <p className="upload-subtitle">
            Upload your textbook and ask any question —<br />
            AI answers <em>only</em> from your book.
          </p>
        </header>

        {/* Drop Zone */}
        <div
          className={`drop-zone ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => !file && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            style={{ display: "none" }}
            onChange={(e) => handleFile(e.target.files[0])}
          />

          {file ? (
            /* File selected state */
            <div className="file-preview">
              <div className="file-icon">📄</div>
              <div className="file-info">
                <p className="file-name">{file.name}</p>
                <p className="file-size">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
              <button
                className="file-remove"
                onClick={(e) => { e.stopPropagation(); setFile(null); setError(""); }}
                title="Remove file"
              >✕</button>
            </div>
          ) : (
            /* Empty state */
            <div className="drop-content">
              <div className="drop-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 16V8M8 12l4-4 4 4" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M20 16.7A4 4 0 0 0 17 9h-.8A7 7 0 1 0 5 15.3" strokeLinecap="round"/>
                </svg>
              </div>
              <p className="drop-text">Drag & drop your PDF here</p>
              <p className="drop-subtext">or <span className="drop-link">click to browse</span></p>
              <p className="drop-limit">PDF only · Max 50MB</p>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="upload-error fade-in">
            <span>⚠</span> {error}
          </div>
        )}

        {/* Success stats (brief moment before navigation) */}
        {success && (
          <div className="upload-success fade-in">
            <span className="success-icon">✓</span>
            <div>
              <p className="success-title">Ready!</p>
              <p className="success-stats">
                {success.total_pages} pages · {success.total_chunks} searchable chunks
              </p>
            </div>
          </div>
        )}

        {/* Upload progress bar */}
        {uploading && !success && (
          <div className="progress-wrap fade-in">
            <div className="progress-label">
              <span>Processing your textbook…</span>
              <span>{progress}%</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <p className="progress-sub">
              {progress < 100 ? "Uploading…" : "Extracting text & generating embeddings…"}
            </p>
          </div>
        )}

        {/* Upload Button */}
        {!uploading && !success && (
          <button
            className="btn-primary upload-btn"
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Upload & Analyse
          </button>
        )}

        {/* How it works */}
        <div className="how-it-works">
          <div className="step"><span className="step-num">1</span><span>Upload your PDF textbook</span></div>
          <div className="step-sep">→</div>
          <div className="step"><span className="step-num">2</span><span>Ask any question</span></div>
          <div className="step-sep">→</div>
          <div className="step"><span className="step-num">3</span><span>Get answers from your book</span></div>
        </div>

      </div>
    </div>
  );
}
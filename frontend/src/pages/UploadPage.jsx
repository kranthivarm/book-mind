// pages/UploadPage.jsx
import { useState, useRef, useCallback } from "react";
import { uploadBook } from "../services/api";
import "../styles/pages/Uploadpage.css";

export default function UploadPage({ onUploadSuccess }) {
  const [dragOver,  setDragOver]  = useState(false);
  const [file,      setFile]      = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress,  setProgress]  = useState(0);
  const [error,     setError]     = useState("");
  const [success,   setSuccess]   = useState(null);
  const fileInputRef = useRef(null);

  const validate = (f) => {
    if (!f) return "No file selected.";
    if (!f.name.endsWith(".pdf") && f.type !== "application/pdf") return "Only PDF files supported.";
    if (f.size > 200 * 1024 * 1024) return "Max size is 50 MB.";
    return null;
  };

  const handleFile = useCallback((f) => {
    setError(""); setSuccess(null);
    const err = validate(f);
    if (err) { setError(err); return; }
    setFile(f);
  }, []);

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setProgress(0); setError("");
    try {
      const data = await uploadBook(file, setProgress);
      setSuccess(data);
      setTimeout(() => onUploadSuccess(data), 1200);
    } catch (err) {
      setError(err.message);
      setUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="blob b1"/><div className="blob b2"/>

      <div className="upload-card fade-up">
        <div className="upload-top">
          <h1 className="upload-heading">New Chat</h1>
          <p className="upload-sub">Upload a textbook PDF to start asking questions</p>
        </div>

        {/* Drop zone */}
        <div
          className={`drop-zone ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => !file && fileInputRef.current?.click()}
          tabIndex={0}
          onKeyDown={e => e.key === "Enter" && fileInputRef.current?.click()}
        >
          <input ref={fileInputRef} type="file" accept=".pdf,application/pdf"
            style={{display:"none"}} onChange={e => handleFile(e.target.files[0])} />

          {file ? (
            <div className="file-row">
              <span className="file-ico">📄</span>
              <div className="file-info">
                <p className="file-name">{file.name}</p>
                <p className="file-size">{(file.size/1024/1024).toFixed(2)} MB</p>
              </div>
              <button className="file-rm" onClick={e => {e.stopPropagation(); setFile(null);}}>✕</button>
            </div>
          ) : (
            <div className="drop-inner">
              <div className="drop-icon-wrap">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 16V8M8 12l4-4 4 4" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M20 16.7A4 4 0 0 0 17 9h-.8A7 7 0 1 0 5 15.3" strokeLinecap="round"/>
                </svg>
              </div>
              <p className="drop-text">Drag & drop your PDF</p>
              <p className="drop-sub">or <span className="drop-link" onClick={() => fileInputRef.current?.click()}>browse</span></p>
              <p className="drop-limit">PDF · Max 200 MB</p>
            </div>
          )}
        </div>

        {error && <div className="upload-error">⚠ {error}</div>}

        {success && (
          <div className="upload-success">
            <span>✓</span>
            <div>
              <p><strong>Ready!</strong></p>
              <p>{success.total_pages} pages · {success.total_chunks} chunks indexed</p>
            </div>
          </div>
        )}

        {uploading && !success && (
          <div className="progress-wrap">
            <div className="progress-row">
              <span>{progress < 100 ? "Uploading…" : "Processing…"}</span>
              <span>{progress}%</span>
            </div>
            <div className="progress-bar"><div className="progress-fill" style={{width:`${progress}%`}}/></div>
          </div>
        )}

        {!uploading && !success && (
          <button className="btn-primary upload-btn" onClick={handleUpload} disabled={!file}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Upload & Start Chat
          </button>
        )}

        <div className="steps">
          <div className="step"><span className="sn">1</span>Upload PDF</div>
          <span className="step-sep">→</span>
          <div className="step"><span className="sn">2</span>Ask questions</div>
          <span className="step-sep">→</span>
          <div className="step"><span className="sn">3</span>Get answers</div>
        </div>
      </div>
    </div>
  );
}
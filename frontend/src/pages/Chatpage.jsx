import { useState, useRef, useEffect } from "react";
import { askQuestion } from "../services/api";
import SourcesPanel from "../components/SourcesPanel";
import "../styles/pages/Chatpage.css";

export default function ChatPage({ bookId, bookName, bookStats, onChangeBook }) {
  //   State 
  const [messages, setMessages]     = useState([]);       // all chat messages
  const [question, setQuestion]     = useState("");       // current input value
  const [isLoading, setIsLoading]   = useState(false);    // waiting for AI

  const messagesEndRef = useRef(null); // used to auto-scroll to bottom
  const inputRef       = useRef(null);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => { inputRef.current?.focus(); }, []);

  //  Send question 
  const handleSend = async () => {
    const q = question.trim();
    if (!q || isLoading) return;

    setQuestion("");
    setIsLoading(true);

    // Add user message immediately (optimistic UI)
    const userMsg = { id: Date.now(), role: "user", text: q };
    // Add a "loading" AI message as placeholder
    const loadingMsg = { id: Date.now() + 1, role: "ai", loading: true };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);

    try {
      // Call backend RAG pipeline
      const data = await askQuestion(bookId, q);
      // data = { answer, question, sources: [{page_number, text_preview, relevance_score}] }

      // Replace the loading placeholder with the real answer
      setMessages((prev) =>
        prev.map((msg) =>
          msg.loading
            ? { id: msg.id, role: "ai", text: data.answer, sources: data.sources }
            : msg
        )
      );
    } catch (err) {
      // Replace loading with error message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.loading
            ? { id: msg.id, role: "ai", text: `⚠ ${err.message}`, isError: true }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  // Send on Enter (Shift+Enter = new line)
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Short filename for display
  const shortName = bookName.length > 30 ? bookName.slice(0, 27) + "…" : bookName;

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="chat-page">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="header-logo">📖</div>
          <div className="header-book-info">
            <span className="header-app-name">PdfChat</span>
            <span className="header-book-name" title={bookName}>
              {shortName}
            </span>
          </div>
        </div>

        {bookStats && (
          <div className="header-stats">
            <div className="stat-pill">
              <span className="stat-icon">📄</span>
              {bookStats.totalPages} pages
            </div>
            <div className="stat-pill">
              <span className="stat-icon">🔍</span>
              {bookStats.totalChunks} chunks
            </div>
          </div>
        )}

        <button className="btn-ghost" onClick={onChangeBook}>
          ← Change Book
        </button>
      </header>

      {/*  Message list */}
      <div className="chat-messages">

        {/* Empty state */}
        {messages.length === 0 && (
          <div className="chat-empty fade-up">
            <div className="empty-icon">💬</div>
            <h2 className="empty-title">Ask anything about your textbook</h2>
            <p className="empty-sub">
              The AI will answer <strong>only</strong> from <em>{shortName}</em>
            </p>
            {/* Suggested questions */}
            <div className="suggestions">
              {[
                "What is the main topic of this book?",
                "Explain the key concepts from chapter 1.",
                "Summarise the most important points.",
              ].map((s) => (
                <button
                  key={s}
                  className="suggestion-chip"
                  onClick={() => { setQuestion(s); inputRef.current?.focus(); }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg) => (
          <div key={msg.id} className={`message-row ${msg.role}`}>
            {/* Avatar */}
            <div className={`msg-avatar ${msg.role}`}>
              {msg.role === "user" ? "👤" : "🤖"}
            </div>

            <div className="msg-content">
              {/* Bubble */}
              <div className={`msg-bubble ${msg.role} ${msg.isError ? "error" : ""}`}>
                {msg.loading ? (
                  /* Typing indicator */
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                ) : (
                  <p className="msg-text">{msg.text}</p>
                )}
              </div>

              {/* Sources accordion — only for AI messages with sources */}
              {msg.role === "ai" && msg.sources?.length > 0 && (
                <SourcesPanel sources={msg.sources} />
              )}
            </div>
          </div>
        ))}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/*  Input bar */}
      <div className="chat-input-bar">
        <div className="input-wrap">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Ask a question about your textbook…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!question.trim() || isLoading}
            title="Send (Enter)"
          >
            {isLoading ? (
              <span className="send-spinner" />
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
          </button>
        </div>
        <p className="input-hint">Enter to send · Shift+Enter for new line</p>
      </div>

    </div>
  );
}
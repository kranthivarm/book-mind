import { useState, useRef, useEffect } from "react";
import { streamQuestion } from "../services/api";
import SourcesPanel from "../components/SourcesPanel";
import "../styles/pages/Chatpage.css";

export default function ChatPage({ bookId, bookName, bookStats, onChangeBook }) {
  const [messages,   setMessages]   = useState([]);
  const [question,   setQuestion]   = useState("");
  const [isLoading,  setIsLoading]  = useState(false);
  const [statusText, setStatusText] = useState(""); // "Searching…" / "Generating…"

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  //  Streaming send
  const handleSend = async () => {
    const q = question.trim();
    if (!q || isLoading) return;

    setQuestion("");
    setIsLoading(true);
    setStatusText("");

    // Add user message immediately
    const userMsgId = Date.now();
    const aiMsgId   = Date.now() + 1;

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: "user", text: q },
      // AI message starts empty — we'll append tokens to it
      { id: aiMsgId, role: "ai", text: "", sources: null, streaming: true },
    ]);

    await streamQuestion(bookId, q, {

      // "Searching your textbook…" / "Generating answer…"
      onStatus: (msg) => {
        setStatusText(msg);
      },

      // Each token: append to the AI message's text
      // We use the functional form of setMessages so we always have latest state
      onToken: (token) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, text: msg.text + token }
              : msg
          )
        );
      },

      // Sources arrive once, after the full answer
      onSources: (sources) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, sources }
              : msg
          )
        );
      },

      // Stream finished
      onDone: () => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, streaming: false }
              : msg
          )
        );
        setIsLoading(false);
        setStatusText("");
        inputRef.current?.focus();
      },

      // Error
      onError: (errMsg) => {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, text: `⚠ ${errMsg}`, isError: true, streaming: false }
              : msg
          )
        );
        setIsLoading(false);
        setStatusText("");
      },
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const shortName = bookName.length > 30 ? bookName.slice(0, 27) + "…" : bookName;

  return (
    <div className="chat-page">

      {/* Header */}
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="header-logo">📖</div>
          <div className="header-book-info">
            <span className="header-app-name">BookMind</span>
            <span className="header-book-name" title={bookName}>{shortName}</span>
          </div>
        </div>
        {bookStats && (
          <div className="header-stats">
            <div className="stat-pill"><span className="stat-icon">📄</span>{bookStats.totalPages} pages</div>
            <div className="stat-pill"><span className="stat-icon">🔍</span>{bookStats.totalChunks} chunks</div>
          </div>
        )}
        <button className="btn-ghost" onClick={onChangeBook}>← Change Book</button>
      </header>

      {/* Message list */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty fade-up">
            <div className="empty-icon">💬</div>
            <h2 className="empty-title">Ask anything about your textbook</h2>
            <p className="empty-sub">
              The AI will answer <strong>only</strong> from <em>{shortName}</em>
            </p>
            <div className="suggestions">
              {[
                "What is the main topic of this book?",
                "Explain the key concepts from chapter 1.",
                "Summarise the most important points.",
              ].map(s => (
                <button key={s} className="suggestion-chip"
                  onClick={() => { setQuestion(s); inputRef.current?.focus(); }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`message-row ${msg.role}`}>
            <div className={`msg-avatar ${msg.role}`}>
              {msg.role === "user" ? "👤" : "🤖"}
            </div>
            <div className="msg-content">
              <div className={`msg-bubble ${msg.role} ${msg.isError ? "error" : ""}`}>
                {/* Show typing indicator only while streaming AND no text yet */}
                {msg.streaming && !msg.text ? (
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                ) : (
                  <>
                    <p className="msg-text">{msg.text}</p>
                    {/* Blinking cursor while streaming */}
                    {msg.streaming && <span className="stream-cursor">▌</span>}
                  </>
                )}
              </div>
              {/* Sources appear after streaming is done */}
              {!msg.streaming && msg.role === "ai" && msg.sources?.length > 0 && (
                <SourcesPanel sources={msg.sources} />
              )}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="chat-input-bar">
        {/* Status text shown above input while loading */}
        {statusText && (
          <p className="stream-status fade-in">{statusText}</p>
        )}
        <div className="input-wrap">
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Ask a question about your textbook…"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />
          <button className="send-btn" onClick={handleSend}
            disabled={!question.trim() || isLoading} title="Send (Enter)">
            {isLoading
              ? <span className="send-spinner" />
              : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              )
            }
          </button>
        </div>
        <p className="input-hint">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
}
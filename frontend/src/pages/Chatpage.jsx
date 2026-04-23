import { useState, useRef, useEffect, useCallback } from "react";
import { getChatMessages, streamQuestion } from "../services/api";
import SourcesPanel from "../components/SourcesPanel";
import "../styles/pages/Chatpage.css";

export default function ChatPage({ chatId, bookId, bookName, bookStats, onChatsChange }) {
  const [messages,   setMessages]   = useState([]);
  const [question,   setQuestion]   = useState("");
  const [isLoading,  setIsLoading]  = useState(false);
  const [statusText, setStatusText] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);

  // Load message history from Postgres when chat opens
  useEffect(() => {
    setLoadingHistory(true);
    getChatMessages(chatId)
      .then(msgs => {
        // Map DB format to local display format
        setMessages(msgs.map(m => ({
          id:       m.message_id,
          role:     m.role,
          text:     m.text,
          sources:  m.sources,
          streaming: false,
        })));
      })
      .catch(console.error)
      .finally(() => {
        setLoadingHistory(false);
        setTimeout(() => messagesEndRef.current?.scrollIntoView(), 80);
      });
    inputRef.current?.focus();
  }, [chatId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const q = question.trim();
    if (!q || isLoading) return;

    setQuestion("");
    setIsLoading(true);
    setStatusText("");

    const aiMsgLocalId = `ai_${Date.now()}`;

    setMessages(prev => [
      ...prev,
      { id: `u_${Date.now()}`, role: "user",  text: q,  streaming: false },
      { id: aiMsgLocalId,       role: "ai",    text: "",  streaming: true, sources: null },
    ]);

    await streamQuestion(bookId, q, chatId, {
      onStatus: setStatusText,

      // Append each token to the AI message
      onToken: (token) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgLocalId ? { ...m, text: m.text + token } : m
          )
        );
      },

      onSources: (sources) => {
        setMessages(prev =>
          prev.map(m => m.id === aiMsgLocalId ? { ...m, sources } : m)
        );
      },

      onDone: () => {
        setMessages(prev =>
          prev.map(m => m.id === aiMsgLocalId ? { ...m, streaming: false } : m)
        );
        setIsLoading(false);
        setStatusText("");
        onChatsChange();  // refresh sidebar preview
        inputRef.current?.focus();
      },

      onError: (errMsg) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgLocalId
              ? { ...m, text: `⚠ ${errMsg}`, isError: true, streaming: false }
              : m
          )
        );
        setIsLoading(false);
        setStatusText("");
      },
    });
  }, [question, isLoading, bookId, chatId, onChatsChange]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const shortName = bookName?.length > 28 ? bookName.slice(0, 25) + "…" : bookName;

  return (
    <div className="chat-page">
      <header className="chat-header">
        <div className="chat-header-book">
          <span className="chat-header-icon">📄</span>
          <div>
            <p className="chat-header-label">Chatting with</p>
            <p className="chat-header-name" title={bookName}>{shortName}</p>
          </div>
        </div>
        {bookStats && (
          <div className="header-pills">
            <span className="header-pill">📖 {bookStats.totalPages} pages</span>
            <span className="header-pill">🔍 {bookStats.totalChunks} chunks</span>
          </div>
        )}
      </header>

      <div className="chat-messages">
        {loadingHistory ? (
          <div className="chat-loading">
            <div className="typing-indicator"><span/><span/><span/></div>
            <p>Loading history…</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty fade-up">
            <div className="empty-icon">💬</div>
            <h2 className="empty-title">Ask anything about your textbook</h2>
            <p className="empty-sub">Answers come only from <em>{shortName}</em></p>
            <div className="suggestions">
              {["What is the main topic?", "Explain chapter 1.", "Give key definitions."].map(s => (
                <button key={s} className="suggestion-chip"
                  onClick={() => { setQuestion(s); inputRef.current?.focus(); }}>{s}</button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={msg.id || idx} className={`message-row ${msg.role}`}>
              <div className={`msg-avatar ${msg.role}`}>{msg.role === "user" ? "👤" : "🤖"}</div>
              <div className="msg-content">
                <div className={`msg-bubble ${msg.role} ${msg.isError ? "error" : ""}`}>
                  {msg.streaming && !msg.text ? (
                    <div className="typing-indicator"><span/><span/><span/></div>
                  ) : (
                    <>
                      <p className="msg-text">{msg.text}</p>
                      {msg.streaming && <span className="stream-cursor">▌</span>}
                    </>
                  )}
                </div>
                {!msg.streaming && msg.role === "ai" && msg.sources?.length > 0 && (
                  <SourcesPanel sources={msg.sources} />
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar">
        {statusText && <p className="stream-status">{statusText}</p>}
        <div className="input-wrap">
          <textarea ref={inputRef} className="chat-input"
            placeholder="Ask a question…" value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown} rows={1} disabled={isLoading} />
          <button className="send-btn" onClick={handleSend}
            disabled={!question.trim() || isLoading}>
            {isLoading ? <span className="send-spinner"/> :
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>}
          </button>
        </div>
        <p className="input-hint">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
}
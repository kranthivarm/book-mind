import { useState, useRef, useEffect, useCallback } from "react";
import { getChatMessages, streamQuestion } from "../services/api";
import SourcesPanel from "../components/SourcesPanel";
import useSpeechRecognition from "../hooks/useSpeechRecognition";
import "../styles/pages/Chatpage.css";

export default function ChatPage({ chatId, bookId, bookName, bookStats, onChatsChange }) {
  const [messages,       setMessages]       = useState([]);
  const [question,       setQuestion]       = useState("");
  const [isLoading,      setIsLoading]      = useState(false);
  const [statusText,     setStatusText]     = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);

  // interimText: the live "preview" of what's being spoken right now
  // shown in the textarea with lower opacity until speech is confirmed
  const [interimText, setInterimText] = useState("");

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);

  //   Speech recognition
  const { isListening, isSupported, error: speechError, toggle: toggleMic } =
    useSpeechRecognition({

      // Called when a word/phrase is fully recognised (user paused)
      // We APPEND to existing question so multiple mic presses accumulate
      onTranscript: (text) => {
        setQuestion(prev => {
          const separator = prev.trim() ? " " : "";
          return prev + separator + text;
        });
        setInterimText("");
        // Focus textarea so user can edit immediately after speaking
        inputRef.current?.focus();
      },

      // Called live as user speaks — shows a preview, not yet committed
      onInterim: (text) => setInterimText(text),
    });

  //   Load history 
  useEffect(() => {
    setLoadingHistory(true);
    getChatMessages(chatId)
      .then(msgs => {
        setMessages(msgs.map(m => ({
          id:        m.message_id,
          role:      m.role,
          text:      m.text,
          sources:   m.sources,
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

  //   Send  
  const handleSend = useCallback(async () => {
    const q = question.trim();
    if (!q || isLoading) return;

    setQuestion("");
    setInterimText("");
    setIsLoading(true);
    setStatusText("");

    const aiMsgLocalId = `ai_${Date.now()}`;

    setMessages(prev => [
      ...prev,
      { id: `u_${Date.now()}`, role: "user", text: q,  streaming: false },
      { id: aiMsgLocalId,      role: "ai",   text: "",  streaming: true, sources: null },
    ]);

    await streamQuestion(bookId, q, chatId, {
      onStatus: setStatusText,
      onToken: (token) => {
        setMessages(prev =>
          prev.map(m => m.id === aiMsgLocalId ? { ...m, text: m.text + token } : m)
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
        onChatsChange();
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

  // The textarea shows: confirmed text + live interim preview
  const displayValue = interimText
    ? question + (question.trim() ? " " : "") + interimText
    : question;

  return (
    <div className="chat-page">

      {/* Header */}
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

      {/* Messages */}
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

      {/* Input bar */}
      <div className="chat-input-bar">
        {statusText && <p className="stream-status">{statusText}</p>}

        {/* Speech error */}
        {speechError && (
          <p className="speech-error">⚠ {speechError}</p>
        )}

        {/* Listening indicator above input */}
        {isListening && (
          <div className="listening-indicator">
            <span className="listening-dot"/><span className="listening-dot"/><span className="listening-dot"/>
            <span className="listening-label">Listening… speak now</span>
          </div>
        )}

        <div className={`input-wrap ${isListening ? "listening" : ""}`}>
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder={isListening ? "Listening… speak your question" : "Ask a question or click 🎤 to speak…"}
            // Show confirmed text + live interim preview while speaking
            // But textarea value stays as `question` (only confirmed text)
            // We show displayValue as a visual trick using a layered approach
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />

          {/* Live interim text shown as ghost overlay */}
          {interimText && (
            <span className="interim-overlay">
              {question}{question.trim() ? " " : ""}<span className="interim-text">{interimText}</span>
            </span>
          )}

          {/* Mic button — only shown if browser supports it */}
          {isSupported && (
            <button
              className={`mic-btn ${isListening ? "active" : ""}`}
              onClick={toggleMic}
              disabled={isLoading}
              title={isListening ? "Stop listening" : "Speak your question"}
              type="button"
            >
              {isListening ? (
                // Animated waveform while listening
                <span className="mic-wave">
                  <span/><span/><span/><span/><span/>
                </span>
              ) : (
                // Mic icon when idle
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <rect x="9" y="2" width="6" height="11" rx="3"/>
                  <path d="M5 10a7 7 0 0 0 14 0"/>
                  <line x1="12" y1="19" x2="12" y2="22"/>
                  <line x1="8"  y1="22" x2="16" y2="22"/>
                </svg>
              )}
            </button>
          )}

          {/* Send button */}
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!question.trim() || isLoading}
            title="Send (Enter)"
          >
            {isLoading ? <span className="send-spinner"/> :
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            }
          </button>
        </div>

        <p className="input-hint">
          Enter to send · Shift+Enter for new line
          {isSupported && " · 🎤 to speak"}
        </p>
      </div>
    </div>
  );
}
// components/Sidebar.jsx
import { useState } from "react";
import  "../styles/components/Sidebar.css"

export default function Sidebar({
  chats, activeChatId, user, onNewChat, onSelectChat, onDeleteChat, onLogout, isOpen, onToggle
}) {
  const [hoveredId, setHoveredId] = useState(null);

  const handleDelete = (e, chatId) => {
    e.stopPropagation();
    if (window.confirm("Delete this chat?")) onDeleteChat(chatId);
  };

  const formatDate = (rawTs) => {
    if (!rawTs) return "";
    const d = new Date(rawTs);
    if (isNaN(d.getTime())) return "";
    const now = new Date();
    const diffDays = Math.floor((now - d) / 86400000);
    if (diffDays === 0) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7)  return d.toLocaleDateString([], { weekday: "short" });
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <aside className={`sidebar ${isOpen ? "open" : "closed"}`}>

      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <span className="sidebar-logo">📖</span>
          <span className="sidebar-title">BookMind</span>
        </div>
        <button className="sidebar-close" onClick={onToggle}>✕</button>
      </div>

      {/* New chat */}
      <button className="new-chat-btn" onClick={onNewChat}>
        <span className="new-chat-icon">＋</span>New Chat
      </button>

      {/* Chat list */}
      <div className="chat-list">
        {chats.length === 0 ? (
          <div className="chat-list-empty">
            <p>No chats yet.</p>
            <p>Upload a textbook to start.</p>
          </div>
        ) : (
          chats.map(chat => (
            <div
              key={chat.chat_id}
              className={`chat-item ${chat.chat_id === activeChatId ? "active" : ""}`}
              onClick={() => onSelectChat(chat.chat_id)}
              onMouseEnter={() => setHoveredId(chat.chat_id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              <div className="chat-item-icon">📄</div>
              <div className="chat-item-body">
                <p className="chat-item-name">{truncate(chat.book_name, 22)}</p>
                <p className="chat-item-preview">
                  {chat.last_message ? truncate(chat.last_message, 30) : "No messages yet"}
                </p>
              </div>
              <div className="chat-item-meta">
                <span className="chat-item-time">{formatDate(chat.last_at)}</span>
                {hoveredId === chat.chat_id && (
                  <button className="chat-delete-btn"
                    onClick={(e) => handleDelete(e, chat.chat_id)}>🗑</button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* User footer with logout */}
      <div className="sidebar-footer">
        <div className="user-row">
          <div className="user-avatar">{user?.username?.[0]?.toUpperCase() || "U"}</div>
          <div className="user-info">
            <p className="user-name">{user?.username}</p>
            <p className="user-email">{truncate(user?.email, 22)}</p>
          </div>
          <button className="logout-btn" onClick={onLogout} title="Log out">⏻</button>
        </div>
      </div>
    </aside>
  );
}

function truncate(str, n) {
  return str && str.length > n ? str.slice(0, n) + "…" : str;
}
import { useState, useEffect } from "react";
import AuthPage   from "./pages/AuthPage";
import Sidebar    from "./components/Sidebar";
import UploadPage from "./pages/UploadPage";
import ChatPage   from "./pages/Chatpage";
import { getMe, logout, getAllChats, createChat, deleteChat } from "./services/api";
import "./styles/global.css";

export default function App() {
  const [user,         setUser]         = useState(null);    // logged-in user or null
  const [authChecked,  setAuthChecked]  = useState(false);   // initial /me check done?
  const [chats,        setChats]        = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [sidebarOpen,  setSidebarOpen]  = useState(true);

  useEffect(() => {
    getMe()
      .then(user => {
        setUser(user);
        if (user) loadChats();
      })
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    const handler = () => { setUser(null); setChats([]); setActiveChatId(null); };
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  const loadChats = () =>
    getAllChats().then(setChats).catch(console.error);

  const handleAuthSuccess = (userData) => {
    setUser(userData);
    loadChats();
  };

  const handleLogout = async () => {
    await logout().catch(() => {});
    setUser(null);
    setChats([]);
    setActiveChatId(null);
  };

  const handleUploadSuccess = async (uploadData) => {
    const chat = await createChat({
      bookId: uploadData.book_id, bookName: uploadData.filename,
      totalPages: uploadData.total_pages, totalChunks: uploadData.total_chunks,
    });
    await loadChats();
    setActiveChatId(chat.chat_id);
  };

  const handleDeleteChat = async (chatId) => {
    await deleteChat(chatId);
    if (activeChatId === chatId) setActiveChatId(null);
    await loadChats();
  };

  if (!authChecked) {
    return (
      <div style={{ display:"flex", alignItems:"center", justifyContent:"center", height:"100vh", background:"#fdf8fb" }}>
        <div style={{ textAlign:"center" }}>
          <div style={{ fontSize:40, marginBottom:12 }}>📖</div>
          <p style={{ color:"#7a6070", fontFamily:"sans-serif" }}>Loading…</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  const activeChat = chats.find(c => c.chat_id === activeChatId) || null;

  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        user={user}
        onNewChat={() => setActiveChatId(null)}
        onSelectChat={(id) => { setActiveChatId(id); setSidebarOpen(false); }}
        onDeleteChat={handleDeleteChat}
        onLogout={handleLogout}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(o => !o)}
      />
      <main className="main-panel">
        <button className="mobile-toggle" onClick={() => setSidebarOpen(o => !o)}>☰</button>
        {activeChat ? (
          <ChatPage
            key={activeChatId}
            chatId={activeChatId}
            bookId={activeChat.book_id}
            bookName={activeChat.book_name}
            bookStats={{ totalPages: activeChat.total_pages, totalChunks: activeChat.total_chunks }}
            onChatsChange={loadChats}
          />
        ) : (
          <UploadPage onUploadSuccess={handleUploadSuccess} />
        )}
      </main>
    </div>
  );
}
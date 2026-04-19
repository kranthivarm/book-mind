// App.jsx
import { useState, useEffect } from "react";
import Sidebar    from "./components/Sidebar";
import UploadPage from "./pages/UploadPage";
import ChatPage   from "./pages/Chatpage";
import { getAllChats, createChat, deleteChat } from "./services/api";
import "./styles/global.css";

export default function App() {
  const [chats,        setChats]        = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [sidebarOpen,  setSidebarOpen]  = useState(true);

  // Load chats from Postgres on mount
  useEffect(() => {
    getAllChats()
      .then(setChats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const refreshChats = () => getAllChats().then(setChats).catch(console.error);

  const activeChat = chats.find(c => c.chat_id === activeChatId) || null;

  // Called by UploadPage after PDF upload succeeds
  const handleUploadSuccess = async (uploadData) => {
    try {
      const chat = await createChat({
        bookId:      uploadData.book_id,
        bookName:    uploadData.filename,
        totalPages:  uploadData.total_pages,
        totalChunks: uploadData.total_chunks,
      });
      await refreshChats();
      setActiveChatId(chat.chat_id);
    } catch (err) {
      console.error("Failed to create chat:", err);
    }
  };

  const handleSelectChat = (chatId) => {
    setActiveChatId(chatId);
    setSidebarOpen(false);
  };

  const handleDeleteChat = async (chatId) => {
    if (!window.confirm("Delete this chat?")) return;
    await deleteChat(chatId);
    if (activeChatId === chatId) setActiveChatId(null);
    await refreshChats();
  };

  return (
    <div className={`app-shell ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
      <Sidebar
        chats={chats}
        loading={loading}
        activeChatId={activeChatId}
        onNewChat={() => setActiveChatId(null)}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
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
            onChatsChange={refreshChats}
          />
        ) : (
          <UploadPage onUploadSuccess={handleUploadSuccess} />
        )}
      </main>
    </div>
  );
}
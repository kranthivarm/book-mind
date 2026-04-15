import { useState } from "react";
import UploadPage from "./pages/UploadPage";
import ChatPage from "./pages/Chatpage";
import "./styles/global.css";

export default function App() {  
  const [page, setPage] = useState("home");

  const [bookId, setBookId] = useState(null);
  const [bookName, setBookName] = useState("");
  const [bookStats, setBookStats] = useState(null); // { total_pages, total_chunks }

  // Called by UploadPage after successful upload
  const handleUploadSuccess = (data) => {
    setBookId(data.book_id);
    setBookName(data.filename);
    setBookStats({ totalPages: data.total_pages, totalChunks: data.total_chunks });
    setPage("chat");
  };

  // Called by ChatPage "← Change Book" button
  const handleChangeBook = () => {
    setBookId(null);
    setBookName("");
    setBookStats(null);
    setPage("home");
  };

  return (
    <div className="app-root">
      {page === "home" && (
        <UploadPage onUploadSuccess={handleUploadSuccess} />
      )}
      {page === "chat" && (
        <ChatPage
          bookId={bookId}
          bookName={bookName}
          bookStats={bookStats}
          onChangeBook={handleChangeBook}
        />
      )}
    </div>
  );
}
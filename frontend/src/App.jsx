import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];

    if (!selectedFile) return;

    // Only allow PDF
    if (selectedFile.type !== "application/pdf") {
      alert("Please upload a PDF file only");
      return;
    }

    setFile(selectedFile);
    setMessage(""); // reset message
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a file first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      setMessage("");

      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const data = await response.json();

      setMessage(" File uploaded successfully!");
      console.log(data);
    } catch (error) {
      console.error(error);
      setMessage(" Error uploading file");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Arial" }}>
      <h2>Upload PDF</h2>

      <input
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
      />

      <br /><br />

      <button onClick={handleUpload} disabled={loading}>
        {loading ? "Uploading..." : "Upload"}
      </button>

      <p>{message}</p>
    </div>
  );
}

export default App;
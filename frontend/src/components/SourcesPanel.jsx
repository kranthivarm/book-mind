// components/SourcesPanel.jsx
import { useState } from "react";
import "../styles/pages/SourcesPanel.css";

export default function SourcesPanel({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;

  return (
    <div className="sources-panel">
      <button className={`sources-toggle ${open ? "open" : ""}`} onClick={() => setOpen(!open)}>
        <span>📚 {sources.length} source{sources.length > 1 ? "s" : ""} from textbook</span>
        <span className={`chev ${open ? "up" : ""}`}>▾</span>
      </button>
      {open && (
        <div className="sources-list">
          {sources.map((src, i) => {
            const pct = Math.round(src.relevance_score * 100);
            const lvl = pct >= 80 ? "high" : pct >= 60 ? "mid" : "low";
            return (
              <div key={i} className="source-card" style={{animationDelay:`${i*.06}s`}}>
                <div className="source-head">
                  <span className="page-badge">📄 Page {src.page_number}</span>
                  <div className="rel-wrap">
                    <div className="rel-bar-bg">
                      <div className={`rel-bar ${lvl}`} style={{width:`${pct}%`}}/>
                    </div>
                    <span className={`rel-pct ${lvl}`}>{pct}%</span>
                  </div>
                </div>
                <p className="source-preview">"{src.text_preview}"</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
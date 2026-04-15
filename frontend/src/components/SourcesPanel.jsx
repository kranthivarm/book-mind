import { useState } from "react";
import "../styles/pages/SourcesPanel.css"

export default function SourcesPanel({ sources }) {
  // Toggle accordion open/closed
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-panel">

      {/* Toggle button */}
      <button
        className={`sources-toggle ${open ? "open" : ""}`}
        onClick={() => setOpen(!open)}
      >
        <span className="sources-toggle-left">
          <span className="sources-icon">📚</span>
          <span className="sources-label">
            {sources.length} source{sources.length > 1 ? "s" : ""} from your textbook
          </span>
        </span>
        <span className={`chevron ${open ? "up" : "down"}`}>▾</span>
      </button>

      {/* Source cards — shown when open */}
      {open && (
        <div className="sources-list fade-in">
          {sources.map((src, i) => (
            <SourceCard key={i} source={src} index={i} />
          ))}
        </div>
      )}

    </div>
  );
}

// ── Individual source card ─────────────────────────────────────────────────────
function SourceCard({ source, index }) {
  const scorePercent = Math.round(source.relevance_score * 100);

  // Color the score bar based on relevance level
  const scoreColor =
    scorePercent >= 80 ? "high" :
    scorePercent >= 60 ? "mid"  : "low";

  return (
    <div className={`source-card fade-in`} style={{ animationDelay: `${index * 0.06}s` }}>

      {/* Card header */}
      <div className="source-card-header">
        <div className="source-page-badge">
          <span className="page-icon">📄</span>
          Page {source.page_number}
        </div>

        {/* Relevance score */}
        <div className="source-relevance">
          <div className="relevance-bar-wrap" title={`${scorePercent}% relevant`}>
            <div
              className={`relevance-bar ${scoreColor}`}
              style={{ width: `${scorePercent}%` }}
            />
          </div>
          <span className={`relevance-label ${scoreColor}`}>{scorePercent}%</span>
        </div>
      </div>

      {/* Excerpt preview */}
      <p className="source-preview">"{source.text_preview}"</p>

    </div>
  );
}
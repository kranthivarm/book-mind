import { useState } from "react";
import "../styles/components/QuizPanel.css"

export default function QuizPanel({ questions, onRetry, onClose }) {
  // answers[i] = option letter chosen by user ("A", "B", "C", "D") or null
  const [answers,   setAnswers]   = useState(() => Array(questions.length).fill(null));
  const [submitted, setSubmitted] = useState(false);

  const allAnswered = answers.every(a => a !== null);

  const score = submitted
    ? answers.filter((a, i) => a === questions[i].correct).length
    : 0;

  const handleSelect = (qIdx, option) => {
    if (submitted) return;   // lock after submit
    setAnswers(prev => prev.map((a, i) => i === qIdx ? option : a));
  };

  const handleSubmit = () => {
    if (!allAnswered) return;
    setSubmitted(true);
  };

  const handleRetry = () => {
    setAnswers(Array(questions.length).fill(null));
    setSubmitted(false);
    onRetry();
  };

  if (!questions?.length) {
    return (
      <div className="quiz-empty">
        <p>No questions generated. Try a different topic.</p>
        <button className="btn-ghost" onClick={onRetry}>Try again</button>
      </div>
    );
  }

  return (
    <div className="quiz-panel">

      {/* Score banner — shown after submit */}
      {submitted && (
        <div className={`score-banner ${score === questions.length ? "perfect" : score >= questions.length / 2 ? "good" : "low"}`}>
          <span className="score-emoji">
            {score === questions.length ? "🏆" : score >= questions.length / 2 ? "👍" : "📚"}
          </span>
          <div>
            <p className="score-text">
              You scored <strong>{score} / {questions.length}</strong>
            </p>
            <p className="score-sub">
              {score === questions.length
                ? "Perfect score! Excellent work."
                : score >= questions.length / 2
                ? "Good job! Review the ones you missed."
                : "Keep studying — you'll get it!"}
            </p>
          </div>
        </div>
      )}

      {/* Questions */}
      <div className="questions-list">
        {questions.map((q, qIdx) => {
          const chosen   = answers[qIdx];
          const isCorrect = chosen === q.correct;

          return (
            <div key={qIdx} className={`question-card ${submitted ? (isCorrect ? "correct" : "wrong") : ""}`}>

              {/* Question text */}
              <p className="question-text">
                <span className="question-num">Q{qIdx + 1}.</span> {q.question}
              </p>

              {/* Options */}
              <div className="options-list">
                {q.options.map((opt) => {
                  // opt looks like "A) Photosynthesis" — extract the letter
                  const letter = opt.charAt(0);
                  const isChosen  = chosen === letter;
                  const isTheCorrect = q.correct === letter;

                  let optClass = "option-btn";
                  if (submitted) {
                    if (isTheCorrect)          optClass += " correct";
                    else if (isChosen)         optClass += " wrong";
                  } else if (isChosen) {
                    optClass += " selected";
                  }

                  return (
                    <button
                      key={letter}
                      className={optClass}
                      onClick={() => handleSelect(qIdx, letter)}
                      disabled={submitted}
                    >
                      <span className="option-letter">{letter}</span>
                      <span className="option-text">{opt.slice(3)}</span>
                      {submitted && isTheCorrect && <span className="option-tick">✓</span>}
                      {submitted && isChosen && !isTheCorrect && <span className="option-cross">✗</span>}
                    </button>
                  );
                })}
              </div>

              {/* Explanation — shown after submit */}
              {submitted && (
                <div className={`explanation ${isCorrect ? "correct" : "wrong"}`}>
                  <span className="explanation-icon">{isCorrect ? "✓" : "✗"}</span>
                  <p>{q.explanation}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Action buttons */}
      <div className="quiz-actions">
        {!submitted ? (
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={!allAnswered}
          >
            Submit Answers
          </button>
        ) : (
          <>
            <button className="btn-ghost" onClick={handleRetry}>Try another topic</button>
            <button className="btn-primary" onClick={onClose}>Done</button>
          </>
        )}
        {!submitted && !allAnswered && (
          <p className="quiz-hint">Answer all questions to submit</p>
        )}
      </div>
    </div>
  );
}
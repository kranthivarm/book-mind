import { useState, useEffect, useRef, useCallback } from "react";

export default function useSpeechRecognition({ onTranscript, onInterim }) {
  const [isListening,  setIsListening]  = useState(false);
  const [isSupported,  setIsSupported]  = useState(false);
  const [error,        setError]        = useState("");
  const recognitionRef = useRef(null);

  // Check browser support on mount
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    setIsSupported(!!SpeechRecognition);
  }, []);

  const start = useCallback(() => {
    setError("");
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError("Speech recognition not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    // continuous: false → stops after a natural pause (one sentence)
    // Set true if you want it to keep listening until manually stopped
    recognition.continuous = false;

    // interimResults: true → we get live partial results as user speaks
    recognition.interimResults = true;

    // Language — change to "hi-IN" for Hindi, "te-IN" for Telugu, etc.
    recognition.lang = "en-IN";

    recognition.onstart = () => setIsListening(true);

    recognition.onresult = (event) => {
      let interimText = "";
      let finalText   = "";

      // event.results is a SpeechRecognitionResultList
      // Each result has isFinal flag and one or more alternatives
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalText += transcript;
        } else {
          interimText += transcript;
        }
      }

      // Show live interim text (greyed out preview)
      if (interimText) onInterim?.(interimText);

      // Append final confirmed text to the input
      if (finalText) onTranscript?.(finalText.trim());
    };

    recognition.onerror = (event) => {
      // "no-speech" is common — user was quiet too long, not a real error
      if (event.error !== "no-speech") {
        setError(
          event.error === "not-allowed"
            ? "Microphone access denied. Please allow mic in browser settings."
            : `Speech error: ${event.error}`
        );
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      onInterim?.("");  // clear interim preview
    };

    recognition.start();
  }, [onTranscript, onInterim]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const toggle = useCallback(() => {
    isListening ? stop() : start();
  }, [isListening, start, stop]);

  return { isListening, isSupported, error, toggle, stop };
}
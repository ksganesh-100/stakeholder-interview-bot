import { useEffect, useRef, useState } from "react";
import { getInterview, sendMessage } from "../api.js";

// The SPIN interview UI. On mount it loads the full conversation so far from the
// backend, so both a fresh start and a resumed (refreshed) session show the real
// state — never a blank slate over a conversation the server already has.
export default function Chat({ interviewId, stakeholderName, projectName, onReset }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Load the conversation so far (handles fresh start AND resume identically).
  useEffect(() => {
    let cancelled = false;
    getInterview(interviewId)
      .then((data) => {
        if (cancelled) return;
        setMessages(data.messages);
        setDone(data.done);
        setRestoring(false);
      })
      .catch((e) => {
        if (cancelled) return;
        // Interview no longer exists (e.g. database was reset) — start clean.
        if (/not found/i.test(e.message)) {
          onReset();
        } else {
          setError(e.message);
          setRestoring(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [interviewId, onReset]);

  async function send() {
    const text = input.trim();
    if (!text || loading || done) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await sendMessage(interviewId, text);
      setMessages((m) => [...m, { role: "ai", text: res.reply }]);
      if (res.done) setDone(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="chat-shell">
      <div className="chat-header">
        <div>
          <div className="title">{projectName}</div>
          <div className="who">Speaking with {stakeholderName}</div>
        </div>
        <button className="btn-ghost" onClick={onReset}>
          Start over
        </button>
      </div>

      <div className="messages">
        {restoring && <div className="typing">Loading your conversation…</div>}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
        {loading && <div className="typing">The consultant is typing…</div>}
        {done && (
          <div className="done-banner">
            ✓ Thank you — your input has been captured. You can close this window.
          </div>
        )}
        {error && <div className="error">{error}</div>}
        <div ref={bottomRef} />
      </div>

      {!done && !restoring && (
        <div className="composer">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type your reply…"
            disabled={loading}
          />
          <button onClick={send} disabled={loading || !input.trim()}>
            Send
          </button>
        </div>
      )}
    </div>
  );
}

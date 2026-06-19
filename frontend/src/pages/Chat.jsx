import { useEffect, useRef, useState } from "react";
import { sendMessage } from "../api.js";

// The SPIN interview UI. Receives the opening consultant message and drives the
// turn-by-turn exchange until the agent signals the interview is complete.
export default function Chat({
  interviewId,
  stakeholderName,
  projectName,
  firstReply,
  onReset,
}) {
  const [messages, setMessages] = useState([{ role: "ai", text: firstReply }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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

      {!done && (
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

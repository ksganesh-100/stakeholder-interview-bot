import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getProject, startInterview } from "../api.js";
import Chat from "./Chat.jsx";

// Stakeholder entry point. Loads the project, collects name + role, then hands
// off to the Chat component. A started interview id is kept in localStorage so
// a refresh resumes the same conversation.
export default function Landing() {
  const { publicId } = useParams();
  const [project, setProject] = useState(null);
  const [error, setError] = useState(null);

  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [starting, setStarting] = useState(false);

  const storageKey = `interview:${publicId}`;
  const [session, setSession] = useState(() => {
    const raw = localStorage.getItem(storageKey);
    return raw ? JSON.parse(raw) : null;
  });

  useEffect(() => {
    getProject(publicId)
      .then(setProject)
      .catch((e) => setError(e.message));
  }, [publicId]);

  async function begin(e) {
    e.preventDefault();
    if (!name.trim() || !role.trim()) return;
    setStarting(true);
    setError(null);
    try {
      const res = await startInterview(publicId, name.trim(), role.trim());
      const s = { interviewId: res.interview_id, name: name.trim() };
      localStorage.setItem(storageKey, JSON.stringify(s));
      setSession(s);
    } catch (e) {
      setError(e.message);
      setStarting(false);
    }
  }

  function reset() {
    localStorage.removeItem(storageKey);
    setSession(null);
    setName("");
    setRole("");
    setStarting(false);
  }

  if (session) {
    return (
      <Chat
        interviewId={session.interviewId}
        stakeholderName={session.name}
        projectName={project?.name || "Discovery"}
        onReset={reset}
      />
    );
  }

  if (error && !project) {
    return (
      <div className="centered">
        <div className="card">
          <h1>Link not found</h1>
          <p className="sub">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="centered">
      <form className="card" onSubmit={begin}>
        <h1>{project ? project.name : "Loading…"}</h1>
        <p className="sub">
          A short, friendly conversation to understand your work and where AI could
          help. About 10 minutes. There are no wrong answers.
        </p>
        <label htmlFor="name">Your name</label>
        <input
          id="name"
          className="field"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Priya Sharma"
        />
        <label htmlFor="role">Your role</label>
        <input
          id="role"
          className="field"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="e.g. Head of Supply Chain"
        />
        <button className="btn" disabled={starting || !name.trim() || !role.trim()}>
          {starting ? "Starting…" : "Start the conversation"}
        </button>
        {error && <div className="error">{error}</div>}
      </form>
    </div>
  );
}

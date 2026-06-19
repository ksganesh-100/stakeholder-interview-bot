import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProjects, createProject } from "../api.js";

// Admin dashboard: passcode gate, project list, and project creation.
// The passcode is kept in sessionStorage and sent on every admin request.
export default function Admin() {
  const [passcode, setPasscode] = useState(
    () => sessionStorage.getItem("adminPasscode") || ""
  );
  const [entered, setEntered] = useState(
    () => !!sessionStorage.getItem("adminPasscode")
  );
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [newLink, setNewLink] = useState(null);

  async function load(code) {
    setLoading(true);
    setError(null);
    try {
      const data = await listProjects(code);
      setProjects(data);
      sessionStorage.setItem("adminPasscode", code);
      setEntered(true);
    } catch (e) {
      setError(e.message);
      setEntered(false);
      sessionStorage.removeItem("adminPasscode");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (entered && passcode) load(passcode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function unlock(e) {
    e.preventDefault();
    if (passcode.trim()) load(passcode.trim());
  }

  async function create(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    try {
      const res = await createProject(passcode, name.trim(), client.trim());
      setName("");
      setClient("");
      const link = `${window.location.origin}/p/${res.public_id}`;
      setNewLink(link);
      load(passcode);
    } catch (e) {
      setError(e.message);
    }
  }

  function logout() {
    sessionStorage.removeItem("adminPasscode");
    setEntered(false);
    setPasscode("");
    setProjects([]);
  }

  if (!entered) {
    return (
      <div className="centered">
        <form className="card" onSubmit={unlock}>
          <h1>Admin</h1>
          <p className="sub">Enter the admin passcode to manage projects.</p>
          <label htmlFor="pc">Passcode</label>
          <input
            id="pc"
            className="field"
            type="password"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
          />
          <button className="btn" disabled={loading || !passcode.trim()}>
            {loading ? "Checking…" : "Unlock"}
          </button>
          {error && <div className="error">{error}</div>}
        </form>
      </div>
    );
  }

  return (
    <div className="admin-wrap">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1>Projects</h1>
          <p className="sub">Create an engagement, share its link, review responses.</p>
        </div>
        <button className="btn-ghost" onClick={logout}>
          Lock
        </button>
      </div>

      <form className="toolbar" onSubmit={create}>
        <div className="grow">
          <label htmlFor="pname">Project name</label>
          <input
            id="pname"
            className="field"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Acme AI Strategy Discovery"
          />
        </div>
        <div className="grow">
          <label htmlFor="pclient">Client (optional)</label>
          <input
            id="pclient"
            className="field"
            value={client}
            onChange={(e) => setClient(e.target.value)}
            placeholder="e.g. Acme Corp"
          />
        </div>
        <button className="btn" disabled={!name.trim()}>
          Create
        </button>
      </form>

      {newLink && (
        <div className="link-box">
          <code>{newLink}</code>
          <button className="btn-ghost" onClick={() => navigator.clipboard?.writeText(newLink)}>
            Copy
          </button>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      <table style={{ marginTop: 22 }}>
        <thead>
          <tr>
            <th>Project</th>
            <th>Client</th>
            <th>Responses</th>
            <th>Share link</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {projects.length === 0 && (
            <tr>
              <td colSpan={5} style={{ color: "var(--muted)" }}>
                No projects yet — create one above.
              </td>
            </tr>
          )}
          {projects.map((p) => {
            const link = `${window.location.origin}/p/${p.public_id}`;
            return (
              <tr key={p.public_id}>
                <td>{p.name}</td>
                <td>{p.client_name || "—"}</td>
                <td>
                  {p.completed} / {p.total}
                </td>
                <td>
                  <button
                    className="btn-ghost"
                    onClick={() => navigator.clipboard?.writeText(link)}
                  >
                    Copy link
                  </button>
                </td>
                <td>
                  <Link className="row-link" to={`/admin/p/${p.public_id}`}>
                    View →
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="muted-note">
        Tip: send the share link to each stakeholder. Each person enters their name
        and role, then has the discovery conversation. Responses appear here.
      </p>
    </div>
  );
}

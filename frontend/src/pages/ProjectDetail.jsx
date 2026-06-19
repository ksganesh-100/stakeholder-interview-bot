import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProjectInterviews, runSynthesis } from "../api.js";

// One stakeholder's structured summary.
function SummaryCard({ iv }) {
  const s = iv.summary;
  return (
    <div className="summary-block">
      <h3>{iv.name}</h3>
      <div className="role">
        {iv.role}{" "}
        <span className={`pill ${iv.status}`}>{iv.status.replace("_", " ")}</span>
      </div>
      {!s && <p style={{ color: "var(--muted)" }}>Interview not completed yet.</p>}
      {s && (
        <>
          <h4>Situation</h4>
          <p>{s.situation}</p>
          <List title="Problems" items={s.problems} />
          <List title="Implications" items={s.implications} />
          <List title="Desired outcomes" items={s.desired_outcomes} />
        </>
      )}
    </div>
  );
}

function List({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <>
      <h4>{title}</h4>
      <ul>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </>
  );
}

function SynthesisView({ data }) {
  const s = data.synthesis;
  return (
    <div className="synthesis">
      <h2>AI Strategy Compass — {data.count} stakeholder(s)</h2>
      <p>{s.engagement_overview}</p>

      <SynList title="Common problems" items={s.common_problems} />
      <SynList title="Cross-cutting implications" items={s.cross_cutting_implications} />
      <SynList title="Shared desired outcomes" items={s.shared_desired_outcomes} />

      <h4>AI opportunities</h4>
      {s.ai_opportunities?.map((o, i) => (
        <div className="opp" key={i}>
          <div className="t">{o.title}</div>
          <div>{o.rationale}</div>
          {o.stakeholders_affected?.length > 0 && (
            <div className="aff">Affects: {o.stakeholders_affected.join(", ")}</div>
          )}
        </div>
      ))}

      <SynList title="Quick wins" items={s.quick_wins} />
      <SynList title="Open questions" items={s.open_questions} />
    </div>
  );
}

function SynList({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <>
      <h4>{title}</h4>
      <ul>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </>
  );
}

export default function ProjectDetail() {
  const { publicId } = useParams();
  const passcode = sessionStorage.getItem("adminPasscode") || "";

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [synth, setSynth] = useState(null);
  const [synthLoading, setSynthLoading] = useState(false);

  useEffect(() => {
    getProjectInterviews(passcode, publicId)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [passcode, publicId]);

  async function generate() {
    setSynthLoading(true);
    setError(null);
    try {
      setSynth(await runSynthesis(passcode, publicId));
    } catch (e) {
      setError(e.message);
    } finally {
      setSynthLoading(false);
    }
  }

  if (error && !data) {
    return (
      <div className="admin-wrap">
        <Link className="back-link" to="/admin">
          ← Back to projects
        </Link>
        <div className="error">{error}</div>
      </div>
    );
  }

  const completedCount =
    data?.interviews.filter((i) => i.status === "completed").length || 0;

  return (
    <div className="admin-wrap">
      <Link className="back-link" to="/admin">
        ← Back to projects
      </Link>
      <h1>{data?.name || "Loading…"}</h1>
      <p className="sub">
        {data?.client_name ? `${data.client_name} · ` : ""}
        {data ? `${completedCount} completed of ${data.interviews.length}` : ""}
      </p>

      <button
        className="btn"
        style={{ width: "auto", marginBottom: 22 }}
        onClick={generate}
        disabled={synthLoading || completedCount < 1}
      >
        {synthLoading
          ? "Synthesising…"
          : completedCount < 1
          ? "No completed responses yet"
          : "Generate AI strategy synthesis"}
      </button>

      {error && data && <div className="error">{error}</div>}
      {synth && <SynthesisView data={synth} />}

      <h2 style={{ fontSize: 18, margin: "28px 0 12px" }}>Responses</h2>
      {data?.interviews.length === 0 && (
        <p style={{ color: "var(--muted)" }}>
          No responses yet. Share the project link to collect them.
        </p>
      )}
      {data?.interviews.map((iv) => (
        <SummaryCard key={iv.id} iv={iv} />
      ))}
    </div>
  );
}

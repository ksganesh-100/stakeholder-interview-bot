# SPIN Stakeholder Interview Bot

A conversational discovery chatbot for AI strategy engagements. Send one link to
your stakeholders; each has a natural, SPIN-structured conversation with a Claude
consultant that draws out their situation, problems, the business impact, and what
"good" would look like. Every interview auto-produces a **structured summary**, and
the admin view aggregates them into an **AI strategy compass** across all stakeholders.

Built on the Anthropic API directly (no LangChain). Model: `claude-sonnet-4-6`.

---

## How it works

```
Stakeholder ──/p/:id──▶ React SPA ──/api──▶ FastAPI ──▶ Claude (SPIN agent)
                                                  │
Admin ──/admin (passcode)──▶ React SPA ──/api──▶  ├──▶ SQLAlchemy (Project, Interview)
                                                  └──▶ Claude (cross-stakeholder synthesis)
```

- **SPIN agent** (`backend/agent.py`): a warm consultant persona that asks one
  question at a time, acknowledges each answer, and walks Situation → Problem →
  Implication → Need-payoff across ~8–12 turns, then wraps up gracefully.
- **Structured output** (`backend/tools.py`): the agent calls a `save_summary` tool
  whose schema is exactly:
  ```json
  { "stakeholder_role": "", "situation": "", "problems": [], "implications": [], "desired_outcomes": [] }
  ```
  Using a tool (not text parsing) guarantees the shape is always valid.
- **Synthesis**: the admin endpoint feeds all completed summaries to Claude and gets
  back the AI strategy compass (common problems, cross-cutting implications, prioritised
  AI opportunities, quick wins, open questions).

---

## Project layout

```
backend/
  agent.py          SPIN system prompt, run_turn() loop, synthesis
  tools.py          save_summary tool + synthesis prompt/tool
  models.py         SQLAlchemy: Project, Interview
  db.py             engine/session (SQLite local, Postgres via DATABASE_URL)
  main.py           FastAPI routes, admin auth, static SPA serving
  requirements.txt
  .env.example
frontend/
  src/pages/        Landing, Chat, Admin, ProjectDetail
  src/api.js        fetch wrappers
  vite.config.js    dev proxy /api -> :8000
render.yaml         Render Blueprint (web service + Postgres)
```

---

## Run locally

You need two terminals.

### 1. Backend

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows
#  ... or: source .venv/bin/activate                # macOS/Linux
pip install -r requirements.txt

cp .env.example .env        # then edit .env
#   ANTHROPIC_API_KEY=sk-ant-...
#   ADMIN_PASSCODE=your-passcode

uvicorn main:app --reload   # serves on http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                 # serves on http://localhost:5173
```

Open:
- **Admin**: http://localhost:5173/admin — enter your passcode, create a project,
  copy its share link.
- **Stakeholder**: open the share link (`/p/<id>`) — enter name + role and chat.
- Complete a couple of interviews, then hit **Generate AI strategy synthesis** in
  the project view.

Environment variables:

| Var | Required | Purpose |
|-----|----------|---------|
| `ANTHROPIC_API_KEY` | yes | Claude API key from console.anthropic.com |
| `ADMIN_PASSCODE` | yes | Unlocks the admin dashboard |
| `DATABASE_URL` | no | Postgres URL; defaults to local SQLite |
| `INTERVIEW_MODEL` | no | Defaults to `claude-sonnet-4-6` |
| `SYNTHESIS_MODEL` | no | Defaults to `claude-sonnet-4-6` (try `claude-opus-4-8` for depth) |

---

## Deploy to Render

1. Push this folder to a Git repo.
2. In Render: **New + → Blueprint**, point it at the repo. `render.yaml` provisions a
   free web service and a free Postgres instance and wires `DATABASE_URL` automatically.
3. Set `ANTHROPIC_API_KEY` and `ADMIN_PASSCODE` in the service's **Environment** tab.
4. Deploy. The build compiles the SPA; FastAPI serves both the API and the SPA from one
   service (same origin, no CORS needed).

**Free-tier notes:** Render free web services sleep after inactivity (first request
wakes them, ~30s), and free Postgres instances expire after ~30 days. Fine for a pilot;
upgrade either plan for a long-running deployment.

---

## Extending

- **Tune the interview**: edit the persona/rules in `system_prompt()` in
  `backend/agent.py`, or the wrap-up pacing constants (`WRAP_UP_AFTER_TURN`, `MAX_TURNS`).
- **Change the summary shape**: edit `SAVE_SUMMARY_TOOL.input_schema` in
  `backend/tools.py` and the rendering in `frontend/src/pages/ProjectDetail.jsx`.
- **Adjust the synthesis**: edit `SYNTHESIS_SYSTEM_PROMPT` / `SAVE_SYNTHESIS_TOOL`.

## Known limitations

- The public interview endpoint has no rate-limiting or abuse protection. It's meant
  for a link shared with known stakeholders. Add throttling before exposing it widely.
- Admin auth is a single shared passcode — adequate for an internal tool, not
  multi-user account management.

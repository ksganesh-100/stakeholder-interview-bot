"""FastAPI application.

Serves the JSON API under /api/* and (in production) the built React SPA for
every other path. Public endpoints drive the stakeholder interview; admin
endpoints (guarded by a single passcode) create projects and run the
cross-stakeholder synthesis.
"""
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

import agent
from db import get_db, init_db
from models import Interview, Project

load_dotenv()

app = FastAPI(title="SPIN Stakeholder Interview Bot")

# CORS is only needed for local dev when the Vite dev server (5173) calls the
# API (8000). In production everything is same-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ── Admin auth ──────────────────────────────────────────────────────────────

def require_admin(x_admin_passcode: str = Header(default="")) -> None:
    """Reject requests whose passcode header doesn't match ADMIN_PASSCODE."""
    expected = os.environ.get("ADMIN_PASSCODE", "")
    if not expected or not secrets.compare_digest(x_admin_passcode, expected):
        raise HTTPException(status_code=401, detail="Invalid admin passcode.")


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateProject(BaseModel):
    name: str
    client_name: str | None = None


class StartInterview(BaseModel):
    name: str
    role: str


class PostMessage(BaseModel):
    message: str


# Synthetic first user turn that prompts the consultant's opening question.
# Filtered out of the displayed transcript.
OPENING_USER_MESSAGE = "Hi — I'm ready to start."


def transcript_to_display(transcript: list[dict]) -> list[dict]:
    """Convert the stored Anthropic transcript into chat bubbles for the UI.

    Keeps stakeholder text and consultant text; drops the synthetic opener,
    tool_use blocks, and tool_result messages.
    """
    out = []
    for m in transcript or []:
        role, content = m.get("role"), m.get("content")
        if role == "user":
            if isinstance(content, str) and content.strip() != OPENING_USER_MESSAGE:
                out.append({"role": "user", "text": content})
            # list content == tool_result -> skip
        elif role == "assistant":
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                text = ""
            if text.strip():
                out.append({"role": "ai", "text": text})
    return out


# ── Public: stakeholder flow ────────────────────────────────────────────────

@app.get("/api/projects/{public_id}")
def get_project(public_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(public_id=public_id).first()
    if not project:
        raise HTTPException(404, "Project not found.")
    return {"name": project.name, "client_name": project.client_name}


@app.post("/api/projects/{public_id}/interviews")
def start_interview(
    public_id: str, body: StartInterview, db: Session = Depends(get_db)
):
    project = db.query(Project).filter_by(public_id=public_id).first()
    if not project:
        raise HTTPException(404, "Project not found.")

    interview = Interview(
        project_id=project.id,
        stakeholder_name=body.name.strip(),
        stakeholder_role=body.role.strip(),
        transcript=[],
        turn_count=0,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    # Kick off with an opening message from the stakeholder so the consultant
    # responds with a warm first question.
    opening = {
        "role": "user",
        "content": OPENING_USER_MESSAGE,
    }
    result = agent.run_turn(
        transcript=[opening],
        stakeholder_name=interview.stakeholder_name,
        stakeholder_role=interview.stakeholder_role,
        turn_count=0,
    )
    interview.transcript = result["transcript"]
    interview.turn_count = 1
    db.commit()

    return {"interview_id": interview.id, "reply": result["reply"], "done": False}


@app.get("/api/interviews/{interview_id}")
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    """Return the conversation so far so the UI can resume mid-interview."""
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(404, "Interview not found.")
    return {
        "name": interview.stakeholder_name,
        "messages": transcript_to_display(interview.transcript),
        "done": interview.status == "completed",
    }


@app.post("/api/interviews/{interview_id}/messages")
def post_message(
    interview_id: int, body: PostMessage, db: Session = Depends(get_db)
):
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(404, "Interview not found.")
    if interview.status == "completed":
        raise HTTPException(409, "This interview is already complete.")

    transcript = list(interview.transcript or [])
    transcript.append({"role": "user", "content": body.message})

    result = agent.run_turn(
        transcript=transcript,
        stakeholder_name=interview.stakeholder_name,
        stakeholder_role=interview.stakeholder_role,
        turn_count=interview.turn_count,
    )

    interview.transcript = result["transcript"]
    interview.turn_count = interview.turn_count + 1

    if result["done"]:
        interview.status = "completed"
        interview.summary_json = result["summary"]
        interview.completed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "reply": result["reply"],
        "done": result["done"],
        "summary": result["summary"],
    }


# ── Admin: projects + synthesis ────────────────────────────────────────────────

@app.post("/api/admin/projects", dependencies=[Depends(require_admin)])
def create_project(body: CreateProject, db: Session = Depends(get_db)):
    public_id = secrets.token_urlsafe(6)
    project = Project(
        public_id=public_id,
        name=body.name.strip(),
        client_name=(body.client_name or "").strip() or None,
    )
    db.add(project)
    db.commit()
    return {"public_id": public_id, "name": project.name}


@app.get("/api/admin/projects", dependencies=[Depends(require_admin)])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    out = []
    for p in projects:
        total = len(p.interviews)
        completed = sum(1 for i in p.interviews if i.status == "completed")
        out.append(
            {
                "public_id": p.public_id,
                "name": p.name,
                "client_name": p.client_name,
                "total": total,
                "completed": completed,
            }
        )
    return out


@app.get(
    "/api/admin/projects/{public_id}/interviews",
    dependencies=[Depends(require_admin)],
)
def project_interviews(public_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(public_id=public_id).first()
    if not project:
        raise HTTPException(404, "Project not found.")
    return {
        "name": project.name,
        "client_name": project.client_name,
        "interviews": [
            {
                "id": i.id,
                "name": i.stakeholder_name,
                "role": i.stakeholder_role,
                "status": i.status,
                "summary": i.summary_json,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in project.interviews
        ],
    }


@app.post(
    "/api/admin/projects/{public_id}/synthesis",
    dependencies=[Depends(require_admin)],
)
def synthesis(public_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(public_id=public_id).first()
    if not project:
        raise HTTPException(404, "Project not found.")

    completed = [
        {
            "name": i.stakeholder_name,
            "role": i.stakeholder_role,
            "summary": i.summary_json,
        }
        for i in project.interviews
        if i.status == "completed" and i.summary_json
    ]
    if len(completed) < 1:
        raise HTTPException(400, "No completed interviews to synthesise yet.")

    return {"count": len(completed), "synthesis": agent.run_synthesis(completed)}


# ── Static SPA (production) ─────────────────────────────────────────────────
# When the frontend has been built, serve it for all non-API routes so the
# single-page app handles client-side routing.

_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")

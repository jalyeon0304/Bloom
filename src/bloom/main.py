from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from bloom.config import settings
from bloom.demo_data import (
    activate_site,
    list_master_sites,
    list_sites,
    series_for_site,
    session_status,
    start_session,
)

app = FastAPI(title=settings.app_name)


class LoginRequestIn(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=4, max_length=128)
    device_name: str = Field(default="unknown-device", max_length=80)


class ApproveIn(BaseModel):
    approver: str = Field(default="admin", max_length=50)


class TokenExchangeIn(BaseModel):
    request_id: str


class SiteActivationIn(BaseModel):
    site_id: str = Field(min_length=2, max_length=20)
    submitted_output_kw: int = Field(gt=0)
    min_power_kw: int | None = Field(default=None, ge=0)
    max_power_kw: int | None = Field(default=None, ge=0)
    target_pct: int | None = Field(default=None, ge=0, le=100)
    deadline_minutes: int | None = Field(default=None, gt=0)
    semi_target_enabled: bool = False
    min_target_minutes: int | None = Field(default=None, gt=0)
    max_target_minutes: int | None = Field(default=None, gt=0)


# demo purpose only: in-memory store (replace with DB/Redis in production)
_pending_login_requests: dict[str, dict] = {}
_session_tokens: dict[str, dict] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/master-sites")
def api_master_sites(group: str | None = Query(default=None)) -> dict:
    return {"items": list_master_sites(group)}


@app.post("/api/sites/activate")
def api_activate_site(payload: SiteActivationIn) -> dict:
    try:
        return activate_site(
            payload.site_id,
            payload.submitted_output_kw,
            payload.min_power_kw,
            payload.max_power_kw,
            payload.target_pct,
            payload.deadline_minutes,
            payload.semi_target_enabled,
            payload.min_target_minutes,
            payload.max_target_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/session/start")
def api_start_session() -> dict:
    return start_session()


@app.get("/api/session/status")
def api_session_status() -> dict:
    return session_status()


@app.get("/api/sites")
def api_sites(group: str | None = Query(default=None)) -> dict:
    return {"items": list_sites(group)}


@app.get("/api/series/{site_id}")
def api_series(site_id: str, points: int = Query(default=30, ge=10, le=180)) -> dict:
    series = series_for_site(site_id, points)
    if not series:
        raise HTTPException(status_code=404, detail="site not found")
    return {"site_id": site_id, "points": series}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    html_path = Path(__file__).with_name("ui_dashboard.html")
    return html_path.read_text(encoding="utf-8")


@app.post("/api/auth/login-request")
def create_login_request(payload: LoginRequestIn) -> dict:
    request_id = str(uuid4())
    now = datetime.now(tz=UTC)
    _pending_login_requests[request_id] = {
        "request_id": request_id,
        "username": payload.username,
        "device_name": payload.device_name,
        "status": "pending",
        "requested_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=3)).isoformat(),
    }
    # NOTE: password is intentionally NOT persisted in this demo flow.
    return {
        "request_id": request_id,
        "status": "pending",
        "message": "관리자 승인 대기 중입니다.",
    }


@app.get("/api/auth/pending")
def list_pending_requests() -> dict:
    now = datetime.now(tz=UTC)
    items = []
    for req in _pending_login_requests.values():
        if req["status"] == "pending" and datetime.fromisoformat(req["expires_at"]) > now:
            items.append(req)
    return {"items": items}


@app.post("/api/auth/approve/{request_id}")
def approve_login_request(request_id: str, payload: ApproveIn) -> dict:
    req = _pending_login_requests.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=409, detail="request already processed")

    now = datetime.now(tz=UTC)
    if datetime.fromisoformat(req["expires_at"]) <= now:
        req["status"] = "expired"
        raise HTTPException(status_code=410, detail="request expired")

    req["status"] = "approved"
    req["approved_by"] = payload.approver
    req["approved_at"] = now.isoformat()
    return {"request_id": request_id, "status": "approved"}


@app.post("/api/auth/token")
def exchange_token(payload: TokenExchangeIn) -> dict:
    req = _pending_login_requests.get(payload.request_id)
    if not req:
        raise HTTPException(status_code=404, detail="request not found")
    if req["status"] != "approved":
        raise HTTPException(status_code=403, detail="not approved")

    token = token_urlsafe(32)
    expires_at = datetime.now(tz=UTC) + timedelta(hours=8)
    _session_tokens[token] = {
        "username": req["username"],
        "device_name": req["device_name"],
        "expires_at": expires_at.isoformat(),
    }

    req["status"] = "completed"
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
    }

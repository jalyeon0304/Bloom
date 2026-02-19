from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
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


class SchedulePatchIn(BaseModel):
    site_id: str
    field: str
    value: str
    user: str | None = None


# demo purpose only: in-memory store (replace with DB/Redis in production)
_pending_login_requests: dict[str, dict] = {}
_session_tokens: dict[str, dict] = {}

_SCHEDULE_ROWS: list[dict[str, str]] = [
    {"site_id": "SKK167", "field": "target_kw", "value": "12000", "status": "active"},
    {"site_id": "SKK046", "field": "min_power_kw", "value": "10200", "status": "active"},
    {"site_id": "KMP000", "field": "target_kw", "value": "2400", "status": "cancel"},
]
_SCHEDULE_LOGS: list[str] = []


def _role_guard(x_role: str | None, allowed: set[str]) -> str:
    role = (x_role or "Viewer").strip()
    if role not in allowed:
        raise HTTPException(status_code=403, detail="forbidden")
    return role


def _now_kst() -> datetime:
    return datetime.now(tz=ZoneInfo("Asia/Seoul"))


def _make_logline(site_id: str, field: str, old: str, new: str, user: str | None) -> str:
    stamp = _now_kst().strftime("%H:%M:%S")
    who = user or "unknown"
    return f"[{stamp}] {site_id} {field} : {old} → {new} (user:{who})"


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
def dashboard(mock: int = Query(default=0)) -> str:
    if mock == 1:
        return ui_kit()
    html_path = Path(__file__).with_name("ui_dashboard.html")
    return html_path.read_text(encoding="utf-8")


@app.get("/ui-kit", response_class=HTMLResponse)
def ui_kit() -> str:
    html_path = Path(__file__).with_name("ui_summary_preview.html")
    fixture_path = Path(__file__).parents[2] / "docs" / "ui" / "fixtures" / "summary.sample.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    html = html_path.read_text(encoding="utf-8")
    return html.replace("__FIXTURE_JSON__", json.dumps(fixture, ensure_ascii=False))


@app.get("/summary", response_class=HTMLResponse)
def summary_preview(mock: int = Query(default=0)) -> str:
    if mock == 1:
        return ui_kit()
    return dashboard()




@app.get("/api/meta")
def api_meta() -> dict:
    now = _now_kst()
    return {"timezone": "Asia/Seoul", "kst_date": now.strftime("%Y-%m-%d"), "generated_at": now.isoformat()}


@app.get("/api/summary")
def api_summary(state: str = Query(default="normal")) -> dict:
    fixture_path = Path(__file__).parents[2] / "docs" / "ui" / "fixtures" / "summary.sample.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    sites = [
        {"site_id": "SKK046", "group": "준중앙", "active": True, "capacity_kw": 19800},
        {"site_id": "SKK056", "group": "준중앙", "active": True, "capacity_kw": 8910},
        {"site_id": "SKK167", "group": "준중앙", "active": True, "capacity_kw": 39600},
        {"site_id": "KMP000", "group": "비중앙", "active": False, "capacity_kw": 6000},
        {"site_id": "SKK000", "group": "비중앙", "active": True, "capacity_kw": 19800},
    ]
    if state == "high-capacity-active":
        payload["summary"]["nameplate_kw"] = 39600
        payload["summary"]["current_output_kw"] = 35200
    if state == "empty":
        payload["series"] = []
        payload["table"] = []
    return {**payload, "sites": sites, "table": _SCHEDULE_ROWS, "logs": _SCHEDULE_LOGS[:50]}


@app.patch("/api/schedule")
def api_patch_schedule(payload: SchedulePatchIn, x_role: str | None = Header(default=None)) -> dict:
    _role_guard(x_role, {"Operator"})
    target = next((r for r in _SCHEDULE_ROWS if r["site_id"] == payload.site_id and r["field"] == payload.field), None)
    if not target:
        target = {"site_id": payload.site_id, "field": payload.field, "value": "", "status": "active"}
        _SCHEDULE_ROWS.append(target)
    old = target["value"]
    target["value"] = payload.value
    if payload.field == "cancel":
        target["status"] = "cancel"
    log_line = _make_logline(payload.site_id, payload.field, old, payload.value, payload.user)
    _SCHEDULE_LOGS.insert(0, log_line)
    return {
        "ok": True,
        "site_id": payload.site_id,
        "field": payload.field,
        "old": old,
        "new": payload.value,
        "logLine": log_line,
        "saved_at": _now_kst().isoformat(),
    }


@app.get("/api/export.xlsx")
def api_export_xlsx(x_role: str | None = Header(default=None)) -> Response:
    _role_guard(x_role, {"Operator"})
    lines = ["site_id,field,value,status"] + [
        f'{r["site_id"]},{r["field"]},{r["value"]},{r["status"]}' for r in _SCHEDULE_ROWS
    ]
    body = "\n".join(lines).encode("utf-8")
    headers = {"Content-Disposition": "attachment; filename=summary_export.xlsx"}
    return Response(content=body, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


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

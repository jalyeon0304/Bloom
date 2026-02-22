from __future__ import annotations

import csv
import re
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from random import Random


SEMI_CENTRAL_SITE_IDS = {"SKK046", "SKK056", "SKK144", "SKK167"}
SKK_SITE_RE = re.compile(r"^SKK\d{3}$")


def _is_skk_site(site_id: str) -> bool:
    return bool(SKK_SITE_RE.match(site_id))


@dataclass
class SiteMaster:
    site_id: str
    site_name: str
    group_type: str
    nameplate_kw: int
    base_output_kw: int


@dataclass
class ActiveSiteConfig:
    site_id: str
    submitted_output_kw: int
    # semi-central fields
    min_power_kw: int | None = None
    max_power_kw: int | None = None
    semi_target_enabled: bool = False
    min_target_minutes: int | None = None
    max_target_minutes: int | None = None
    # non-central fields
    target_pct: int | None = None
    target_kw: int | None = None
    deadline_minutes: int | None = None


_rng = Random(42)

def _normalize_device_code(device_code: str) -> str:
    code = device_code.strip().replace("\u00a0", " ").upper().replace(" ", "")
    if not code:
        raise ValueError("empty device code")

    stamp_match = re.match(r"^([A-Z]+\d+)\.[A-Z]$", code)
    if stamp_match:
        return stamp_match.group(1)

    decimal_match = re.match(r"^([A-Z]+)(\d+)\.0+$", code)
    if decimal_match:
        prefix, num = decimal_match.groups()
        return f"{prefix}{int(num):03d}"

    return code


def _load_site_masters() -> list[SiteMaster]:
    capacity_by_site: dict[str, int] = {}
    rows_path = Path(__file__).with_name("stamp_capacity.tsv")
    with rows_path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp, delimiter="\t")
        for row in reader:
            site_id = _normalize_device_code(row["device_code"])
            if not _is_skk_site(site_id):
                warnings.warn(f"Ignoring non-SKK site in master load: {site_id}")
                continue
            capacity_kw = int(float(row["capacity_kw"]))
            capacity_by_site[site_id] = capacity_by_site.get(site_id, 0) + capacity_kw

    masters: list[SiteMaster] = []
    for site_id in sorted(capacity_by_site):
        group_type = "준중앙" if site_id in SEMI_CENTRAL_SITE_IDS else "비중앙"
        nameplate_kw = capacity_by_site[site_id]
        masters.append(
            SiteMaster(
                site_id=site_id,
                site_name=f"{group_type}-{site_id}",
                group_type=group_type,
                nameplate_kw=nameplate_kw,
                base_output_kw=int(nameplate_kw * 0.86),
            )
        )
    return masters


_SITE_MASTERS: list[SiteMaster] = _load_site_masters()

_ACTIVE_CONFIGS: dict[str, ActiveSiteConfig] = {}
_SESSION_STATE: dict[str, str | None] = {"started_at": None}
_OPEN_OUTPUTS: dict[str, int] = {}
_SEMI_PROGRESS: dict[str, dict[str, str | None]] = {}


def _find_master(site_id: str) -> SiteMaster | None:
    return next((s for s in _SITE_MASTERS if s.site_id == site_id), None)


def _current_output_kw(master: SiteMaster) -> int:
    drift = _rng.uniform(-250, 250)
    return max(0, int(master.base_output_kw + drift))


def _ratio_pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return (numerator / denominator) * 100


def list_master_sites(group_type: str | None = None) -> list[dict]:
    rows = [s for s in _SITE_MASTERS if group_type in (None, "전체") or s.group_type == group_type]
    return [
        {
            "site_id": s.site_id,
            "site_name": s.site_name,
            "group_type": s.group_type,
            "nameplate_kw": s.nameplate_kw,
            "is_active": s.site_id in _ACTIVE_CONFIGS,
        }
        for s in rows
    ]


def activate_site(
    site_id: str,
    submitted_output_kw: int,
    min_power_kw: int | None,
    max_power_kw: int | None,
    target_pct: int | None,
    deadline_minutes: int | None,
    semi_target_enabled: bool,
    min_target_minutes: int | None,
    max_target_minutes: int | None,
) -> dict:
    master = _find_master(site_id)
    if not master:
        raise ValueError("site not found")

    if master.group_type == "준중앙":
        if min_power_kw is None or max_power_kw is None:
            raise ValueError("semi-central requires min_power_kw and max_power_kw")
        if min_power_kw > max_power_kw:
            raise ValueError("min_power must be less than or equal to max_power")
        if semi_target_enabled:
            if not min_target_minutes or not max_target_minutes:
                raise ValueError("semi target-time enabled: min/max target minutes are required")
            if min_target_minutes <= 0 or max_target_minutes <= 0:
                raise ValueError("semi target minutes must be positive")

        conf = ActiveSiteConfig(
            site_id=site_id,
            submitted_output_kw=submitted_output_kw,
            min_power_kw=min_power_kw,
            max_power_kw=max_power_kw,
            semi_target_enabled=semi_target_enabled,
            min_target_minutes=min_target_minutes,
            max_target_minutes=max_target_minutes,
        )
    else:
        if target_pct is None:
            raise ValueError("non-central requires target_pct (0/40/60 etc)")
        if target_pct < 0 or target_pct > 100:
            raise ValueError("target_pct must be between 0 and 100")
        if deadline_minutes is None or deadline_minutes <= 0:
            raise ValueError("non-central requires positive deadline_minutes")

        target_kw = int(master.nameplate_kw * target_pct / 100)
        conf = ActiveSiteConfig(
            site_id=site_id,
            submitted_output_kw=submitted_output_kw,
            target_pct=target_pct,
            target_kw=target_kw,
            deadline_minutes=deadline_minutes,
        )

    _ACTIVE_CONFIGS[site_id] = conf
    _SEMI_PROGRESS.setdefault(site_id, {"min_reached_at": None, "max_reached_at": None})

    return {
        "site_id": site_id,
        "group_type": master.group_type,
        "status": "active",
        "submitted_output_kw": submitted_output_kw,
        "min_power_kw": conf.min_power_kw,
        "max_power_kw": conf.max_power_kw,
        "semi_target_enabled": conf.semi_target_enabled,
        "min_target_minutes": conf.min_target_minutes,
        "max_target_minutes": conf.max_target_minutes,
        "target_pct": conf.target_pct,
        "target_kw": conf.target_kw,
        "deadline_minutes": conf.deadline_minutes,
    }


def start_session() -> dict:
    started_at = datetime.now(tz=UTC).isoformat()
    _SESSION_STATE["started_at"] = started_at
    _OPEN_OUTPUTS.clear()

    for site_id in _ACTIVE_CONFIGS:
        master = _find_master(site_id)
        if master:
            _OPEN_OUTPUTS[site_id] = _current_output_kw(master)
        _SEMI_PROGRESS[site_id] = {"min_reached_at": None, "max_reached_at": None}

    return {"started_at": started_at, "captured_sites": len(_OPEN_OUTPUTS)}


def session_status() -> dict:
    return {"started_at": _SESSION_STATE["started_at"], "captured_sites": len(_OPEN_OUTPUTS)}


def list_sites(group_type: str | None = None) -> list[dict]:
    items: list[dict] = []
    session_started_at = _SESSION_STATE.get("started_at")
    started_dt = datetime.fromisoformat(session_started_at) if session_started_at else None
    now = datetime.now(tz=UTC)

    for site_id, conf in _ACTIVE_CONFIGS.items():
        master = _find_master(site_id)
        if not master:
            continue
        if group_type not in (None, "전체") and master.group_type != group_type:
            continue

        current_output_kw = _current_output_kw(master)
        open_output_kw = _OPEN_OUTPUTS.get(site_id, current_output_kw)
        open_vs_submitted_pct = _ratio_pct(open_output_kw, conf.submitted_output_kw)

        open_gap_alert = False
        open_gap_diff_pct = None
        if open_vs_submitted_pct is not None:
            open_gap_diff_pct = abs(open_vs_submitted_pct - 100)
            open_gap_alert = open_gap_diff_pct >= 10

        base = {
            "site_id": site_id,
            "site_name": master.site_name,
            "group_type": master.group_type,
            "nameplate_kw": master.nameplate_kw,
            "submitted_output_kw": conf.submitted_output_kw,
            "open_output_kw": open_output_kw,
            "current_output_kw": current_output_kw,
            "open_vs_submitted_pct": open_vs_submitted_pct,
            "open_gap_diff_pct": open_gap_diff_pct,
            "open_gap_alert": open_gap_alert,
        }

        if master.group_type == "준중앙":
            assert conf.min_power_kw is not None and conf.max_power_kw is not None
            min_low = conf.min_power_kw * 0.95
            min_high = conf.min_power_kw * 1.05
            max_low = conf.max_power_kw * 0.95
            max_high = conf.max_power_kw * 1.05
            in_min_band = min_low <= current_output_kw <= min_high
            in_max_band = max_low <= current_output_kw <= max_high

            progress = _SEMI_PROGRESS.setdefault(site_id, {"min_reached_at": None, "max_reached_at": None})
            if in_min_band and progress["min_reached_at"] is None:
                progress["min_reached_at"] = now.isoformat()
            if in_max_band and progress["max_reached_at"] is None:
                progress["max_reached_at"] = now.isoformat()

            min_reached_at = datetime.fromisoformat(progress["min_reached_at"]) if progress["min_reached_at"] else None
            max_reached_at = datetime.fromisoformat(progress["max_reached_at"]) if progress["max_reached_at"] else None

            min_deadline_at = (
                started_dt + timedelta(minutes=conf.min_target_minutes)
                if started_dt and conf.min_target_minutes
                else None
            )
            max_deadline_at = (
                started_dt + timedelta(minutes=conf.max_target_minutes)
                if started_dt and conf.max_target_minutes
                else None
            )

            min_within_deadline = (
                min_reached_at is not None and min_deadline_at is not None and min_reached_at <= min_deadline_at
            )
            max_within_deadline = (
                max_reached_at is not None and max_deadline_at is not None and max_reached_at <= max_deadline_at
            )

            if conf.semi_target_enabled:
                semi_success = min_within_deadline and max_within_deadline
            else:
                semi_success = in_min_band or in_max_band

            base.update(
                {
                    "mode": "semi-central",
                    "min_power_kw": conf.min_power_kw,
                    "max_power_kw": conf.max_power_kw,
                    "min_vs_submitted_pct": _ratio_pct(conf.min_power_kw, conf.submitted_output_kw),
                    "min_vs_open_pct": _ratio_pct(conf.min_power_kw, open_output_kw),
                    "max_vs_submitted_pct": _ratio_pct(conf.max_power_kw, conf.submitted_output_kw),
                    "max_vs_open_pct": _ratio_pct(conf.max_power_kw, open_output_kw),
                    "semi_tolerance_pct": 5,
                    "semi_target_enabled": conf.semi_target_enabled,
                    "min_target_minutes": conf.min_target_minutes,
                    "max_target_minutes": conf.max_target_minutes,
                    "min_deadline_at": min_deadline_at.isoformat() if min_deadline_at else None,
                    "max_deadline_at": max_deadline_at.isoformat() if max_deadline_at else None,
                    "min_reached_at": progress["min_reached_at"],
                    "max_reached_at": progress["max_reached_at"],
                    "min_within_deadline": min_within_deadline,
                    "max_within_deadline": max_within_deadline,
                    "semi_success": semi_success,
                }
            )
        else:
            assert conf.target_kw is not None and conf.target_pct is not None and conf.deadline_minutes is not None
            deadline_at = None
            reached_target = current_output_kw <= conf.target_kw
            within_deadline = None
            if started_dt:
                deadline_at = started_dt + timedelta(minutes=conf.deadline_minutes)
                within_deadline = now <= deadline_at and reached_target

            base.update(
                {
                    "mode": "non-central",
                    "target_pct": conf.target_pct,
                    "target_kw": conf.target_kw,
                    "deadline_minutes": conf.deadline_minutes,
                    "deadline_at": deadline_at.isoformat() if deadline_at else None,
                    "reached_target": reached_target,
                    "within_deadline": within_deadline,
                    "target_vs_nameplate_pct": _ratio_pct(conf.target_kw, master.nameplate_kw),
                    "target_vs_submitted_pct": _ratio_pct(conf.target_kw, conf.submitted_output_kw),
                    "target_vs_open_pct": _ratio_pct(conf.target_kw, open_output_kw),
                }
            )

        items.append(base)

    return items


def series_for_site(site_id: str, points: int = 30) -> list[dict]:
    master = _find_master(site_id)
    if not master:
        return []

    now = datetime.now().replace(second=0, microsecond=0)
    value = _current_output_kw(master)
    out: list[dict] = []
    for i in range(points):
        ts = now - timedelta(minutes=points - i)
        drift = _rng.uniform(-180, 180)
        value = max(0, int(value + drift))
        out.append({"measured_at": ts.isoformat(), "kw": value})
    return out

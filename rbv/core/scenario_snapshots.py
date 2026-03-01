from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable

try:  # optional, keep module usable without numpy at import time
    import numpy as _np  # type: ignore[import]
except Exception:  # pragma: no cover
    _np = None  # type: ignore[assignment]

SCENARIO_CONFIG_SCHEMA = "rbv.scenario_config.v1"
SCENARIO_SNAPSHOT_SCHEMA = "rbv.scenario_snapshot.v1"


def _normalize_float(x: float) -> int | float | None:
    try:
        v = float(x)
    except Exception:
        return None
    if not math.isfinite(v):
        return None
    # Collapse signed zero and tiny floating noise for stable hashes across reruns/platforms.
    if abs(v) < 1e-15:
        v = 0.0
    # 12 significant digits is plenty for UI/session inputs while remaining deterministic.
    v = float(f"{v:.12g}")
    if abs(v - round(v)) <= 1e-12:
        return int(round(v))
    return v


def canonicalize_jsonish(value: Any) -> Any:
    """Return a JSON-safe, deterministically ordered representation.

    Used for scenario hashing and snapshot storage. Best-effort normalization only;
    unknown objects are stringified instead of raising.
    """
    if _np is not None:
        try:
            if isinstance(value, _np.generic):
                value = value.item()
        except Exception:
            pass

    if value is None or isinstance(value, (str, bool)):
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)

    if isinstance(value, float):
        return _normalize_float(value)

    if isinstance(value, (_dt.datetime, _dt.date)):
        # Datetime gets ISO string; keep offset if present.
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k in sorted(value.keys(), key=lambda x: str(x)):
            out[str(k)] = canonicalize_jsonish(value[k])
        return out

    if isinstance(value, (list, tuple)):
        return [canonicalize_jsonish(v) for v in value]

    if isinstance(value, set):
        # Sort on canonical JSON to ensure determinism.
        items = [canonicalize_jsonish(v) for v in value]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True))

    # Common duck-types (e.g., pandas Timestamp) often expose isoformat()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    try:
        return json.loads(json.dumps(value))
    except Exception:
        return str(value)


def _filter_state(state: dict[str, Any] | None, allowed_keys: Iterable[str] | None = None) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    src = dict(state)
    if allowed_keys is None:
        return src
    allowed = {str(k) for k in allowed_keys}
    return {k: v for k, v in src.items() if str(k) in allowed}


@dataclass(frozen=True)
class ScenarioConfig:
    state: dict[str, Any] = field(default_factory=dict)
    schema: str = SCENARIO_CONFIG_SCHEMA

    def __post_init__(self) -> None:
        # Freeze a shallow copy to avoid external mutation changing hashes.
        state = self.state if isinstance(self.state, dict) else {}
        object.__setattr__(self, "state", dict(state))
        object.__setattr__(self, "schema", str(self.schema or SCENARIO_CONFIG_SCHEMA))

    @property
    def canonical_state(self) -> dict[str, Any]:
        return canonicalize_jsonish(self.state)  # type: ignore[no-any-return]

    def canonical_json(self) -> str:
        return json.dumps(self.canonical_state, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def deterministic_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        state = self.canonical_state
        return {
            "schema": self.schema,
            "state": state,
            "hash": hashlib.sha256(
                json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            ).hexdigest(),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any] | None, *, allowed_keys: Iterable[str] | None = None) -> "ScenarioConfig":
        return cls(state=_filter_state(state, allowed_keys=allowed_keys))

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "ScenarioConfig":
        obj = dict(payload or {})
        if isinstance(obj.get("config"), dict):
            cfg = obj["config"]
            return cls(state=dict(cfg.get("state") or {}), schema=str(cfg.get("schema") or SCENARIO_CONFIG_SCHEMA))
        if "state" in obj and isinstance(obj.get("state"), dict):
            return cls(
                state=dict(obj.get("state") or {}),
                schema=str(obj.get("schema") or SCENARIO_CONFIG_SCHEMA),
            )
        # Back-compat: treat bare dict as state
        return cls(state=obj)


@dataclass(frozen=True)
class ScenarioSnapshot:
    config: ScenarioConfig
    slot: str = "active"
    label: str | None = None
    app: str = "Rent vs Buy Simulator"
    version: str | None = None
    exported_at: str = field(default_factory=lambda: _dt.datetime.now().isoformat(timespec="seconds"))
    meta: dict[str, Any] = field(default_factory=dict)
    schema: str = SCENARIO_SNAPSHOT_SCHEMA

    def __post_init__(self) -> None:
        cfg = self.config if isinstance(self.config, ScenarioConfig) else ScenarioConfig.from_payload(self.config)
        object.__setattr__(self, "config", cfg)
        object.__setattr__(self, "meta", dict(self.meta or {}))
        object.__setattr__(self, "slot", str(self.slot or "active"))
        object.__setattr__(self, "schema", str(self.schema or SCENARIO_SNAPSHOT_SCHEMA))

    @property
    def scenario_hash(self) -> str:
        return self.config.deterministic_hash()

    def to_dict(self) -> dict[str, Any]:
        cfg_dict = self.config.to_dict()
        return {
            "schema": self.schema,
            "app": self.app,
            "version": self.version,
            "exported_at": self.exported_at,
            "slot": self.slot,
            "label": self.label,
            "scenario_hash": cfg_dict.get("hash"),
            "config": cfg_dict,
            # Back-compat convenience for old importers that only look for `state`
            "state": cfg_dict.get("state", {}),
            "meta": canonicalize_jsonish(self.meta),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "ScenarioSnapshot":
        obj = dict(payload or {})
        cfg = ScenarioConfig.from_payload(obj)
        return cls(
            config=cfg,
            slot=str(obj.get("slot") or "active"),
            label=(None if obj.get("label") is None else str(obj.get("label"))),
            app=str(obj.get("app") or "Rent vs Buy Simulator"),
            version=(None if obj.get("version") is None else str(obj.get("version"))),
            exported_at=str(obj.get("exported_at") or _dt.datetime.now().isoformat(timespec="seconds")),
            meta=(dict(obj.get("meta")) if isinstance(obj.get("meta"), dict) else {}),  # type: ignore[arg-type]
            schema=str(obj.get("schema") or SCENARIO_SNAPSHOT_SCHEMA),
        )


def build_scenario_config(state: dict[str, Any] | None, *, allowed_keys: Iterable[str] | None = None) -> ScenarioConfig:
    return ScenarioConfig.from_state(state, allowed_keys=allowed_keys)


def scenario_hash_from_state(state: dict[str, Any] | None, *, allowed_keys: Iterable[str] | None = None) -> str:
    return build_scenario_config(state, allowed_keys=allowed_keys).deterministic_hash()


def build_scenario_snapshot(
    state: dict[str, Any] | None,
    *,
    slot: str = "active",
    label: str | None = None,
    app: str = "Rent vs Buy Simulator",
    version: str | None = None,
    meta: dict[str, Any] | None = None,
    allowed_keys: Iterable[str] | None = None,
) -> ScenarioSnapshot:
    return ScenarioSnapshot(
        config=build_scenario_config(state, allowed_keys=allowed_keys),
        slot=slot,
        label=label,
        app=app,
        version=version,
        meta=dict(meta or {}),
    )


def _to_float_or_none(v: Any) -> float | None:
    try:
        x = float(v)
    except Exception:
        return None
    if not math.isfinite(x):
        return None
    return x


def extract_terminal_metrics(
    df: Any,
    *,
    close_cash: Any = None,
    monthly_payment: Any = None,
    win_pct: Any = None,
) -> dict[str, float | None]:
    """Extract comparable terminal metrics from a simulation output dataframe (best-effort)."""
    out: dict[str, float | None] = {
        "buyer_nw_final": None,
        "renter_nw_final": None,
        "advantage_final": None,
        "buyer_pv_nw_final": None,
        "renter_pv_nw_final": None,
        "pv_advantage_final": None,
        "buyer_unrecoverable_final": None,
        "renter_unrecoverable_final": None,
        "close_cash": _to_float_or_none(close_cash),
        "monthly_payment": _to_float_or_none(monthly_payment),
        "win_pct": _to_float_or_none(win_pct),
    }
    try:
        if df is None or len(df) == 0:  # type: ignore[arg-type]
            return out
        row = df.iloc[-1]
    except Exception:
        return out

    if row is None:
        return out

    def _row(col: str) -> float | None:
        try:
            return _to_float_or_none(row.get(col))
        except Exception:
            try:
                return _to_float_or_none(row[col])
            except Exception:
                return None

    out["buyer_nw_final"] = _row("Buyer Net Worth")
    out["renter_nw_final"] = _row("Renter Net Worth")
    if (out["buyer_nw_final"] is not None) and (out["renter_nw_final"] is not None):
        out["advantage_final"] = float(out["buyer_nw_final"] - out["renter_nw_final"])

    out["buyer_pv_nw_final"] = _row("Buyer PV NW")
    out["renter_pv_nw_final"] = _row("Renter PV NW")
    if (out["buyer_pv_nw_final"] is not None) and (out["renter_pv_nw_final"] is not None):
        out["pv_advantage_final"] = float(out["buyer_pv_nw_final"] - out["renter_pv_nw_final"])

    out["buyer_unrecoverable_final"] = _row("Buyer Unrecoverable")
    out["renter_unrecoverable_final"] = _row("Renter Unrecoverable")
    return out


def compare_metric_rows(
    metrics_a: dict[str, Any] | None,
    metrics_b: dict[str, Any] | None,
    *,
    atol: float = 1e-9,
) -> list[dict[str, Any]]:
    """Build A/B metric compare rows with absolute and percent deltas (B − A)."""
    a = dict(metrics_a or {})
    b = dict(metrics_b or {})
    specs = [
        ("Final Buyer Net Worth", "buyer_nw_final"),
        ("Final Renter Net Worth", "renter_nw_final"),
        ("Final Net Advantage", "advantage_final"),
        ("Final Buyer PV NW", "buyer_pv_nw_final"),
        ("Final Renter PV NW", "renter_pv_nw_final"),
        ("Final PV Advantage", "pv_advantage_final"),
        ("Final Buyer Unrecoverable", "buyer_unrecoverable_final"),
        ("Final Renter Unrecoverable", "renter_unrecoverable_final"),
        ("Cash to Close", "close_cash"),
        ("Monthly Payment", "monthly_payment"),
        ("Win %", "win_pct"),
    ]
    rows: list[dict[str, Any]] = []
    for label, key in specs:
        va = _to_float_or_none(a.get(key))
        vb = _to_float_or_none(b.get(key))
        delta = None
        pct_delta = None
        if (va is not None) and (vb is not None):
            d = float(vb - va)
            if abs(d) <= float(atol):
                d = 0.0
            delta = d
            if abs(va) > float(atol):
                pct_delta = (d / abs(va)) * 100.0
            elif abs(d) <= float(atol):
                pct_delta = 0.0
        rows.append({"metric": label, "a": va, "b": vb, "delta": delta, "pct_delta": pct_delta})
    return rows


def scenario_state_diff_rows(
    state_a: dict[str, Any] | None,
    state_b: dict[str, Any] | None,
    *,
    atol: float = 1e-9,
) -> list[dict[str, Any]]:
    """Canonical A/B state diff rows (stable sort; ignores tiny float noise)."""
    a_raw = canonicalize_jsonish(state_a or {})
    b_raw = canonicalize_jsonish(state_b or {})
    a = a_raw if isinstance(a_raw, dict) else {}
    b = b_raw if isinstance(b_raw, dict) else {}
    rows: list[dict[str, Any]] = []
    for k in sorted(set(a.keys()) | set(b.keys())):
        va = a.get(k)
        vb = b.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            try:
                if math.isfinite(float(va)) and math.isfinite(float(vb)) and abs(float(va) - float(vb)) <= float(atol):
                    continue
            except Exception:
                pass
        if va != vb:
            rows.append({"key": str(k), "a": va, "b": vb})
    return rows


def parse_scenario_payload(payload: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (state, metadata) from legacy or v1 snapshot payloads."""
    snap = ScenarioSnapshot.from_payload(payload)
    meta: dict[str, Any] = {
        "slot": snap.slot,
        "label": snap.label,
        "scenario_hash": snap.scenario_hash,
        "schema": snap.schema,
        "version": snap.version,
        "exported_at": snap.exported_at,
        "app": snap.app,
    }

    # Preserve any payload-provided metadata (e.g., UI context such as city preset identity).
    payload_meta = snap.meta if isinstance(snap.meta, dict) else {}
    payload_meta_c = canonicalize_jsonish(payload_meta) if isinstance(payload_meta, dict) else {}
    meta["payload_meta"] = payload_meta_c
    # Also lift commonly useful keys to the top-level meta for convenience (without overriding core fields).
    if isinstance(payload_meta_c, dict):
        for k, v in payload_meta_c.items():
            if str(k) not in meta:
                meta[str(k)] = v

    return dict(snap.config.canonical_state), meta


def rows_to_csv_text(rows: list[dict[str, Any]] | None, *, columns: list[str] | tuple[str, ...] | None = None) -> str:
    """Serialize rows to CSV text with stable column ordering."""
    data = [dict(r or {}) for r in (rows or [])]
    if columns is None:
        seen: list[str] = []
        seen_set: set[str] = set()
        for r in data:
            for k in r.keys():
                sk = str(k)
                if sk not in seen_set:
                    seen.append(sk)
                    seen_set.add(sk)
        columns = tuple(seen)
    else:
        columns = tuple(str(c) for c in columns)

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for row in data:
        out: dict[str, Any] = {}
        for c in columns:
            v = canonicalize_jsonish(row.get(c))
            if isinstance(v, (dict, list)):
                out[c] = json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            elif v is None:
                out[c] = ""
            else:
                out[c] = v
        w.writerow(out)
    return buf.getvalue()


def compare_metric_rows_to_csv_text(rows: list[dict[str, Any]] | None) -> str:
    return rows_to_csv_text(rows, columns=["metric", "a", "b", "delta", "pct_delta"])


def scenario_state_diff_rows_to_csv_text(rows: list[dict[str, Any]] | None) -> str:
    return rows_to_csv_text(rows, columns=["key", "a", "b"])


def build_compare_export_payload(
    *,
    payload_a: dict[str, Any] | None,
    payload_b: dict[str, Any] | None,
    metric_rows: list[dict[str, Any]] | None,
    state_diff_rows: list[dict[str, Any]] | None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe compare export payload for PR11 exports."""

    def _snap_meta(payload: dict[str, Any] | None) -> dict[str, Any]:
        try:
            _state, _meta = parse_scenario_payload(payload or {})
            return canonicalize_jsonish(_meta) if isinstance(_meta, dict) else {}  # type: ignore[no-any-return]
        except Exception:
            return {}

    return {
        "schema": "rbv.compare_export.v1",
        "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "meta": canonicalize_jsonish(meta or {}),
        "snapshots": {
            "A": canonicalize_jsonish(payload_a or {}),
            "B": canonicalize_jsonish(payload_b or {}),
        },
        "snapshot_meta": {
            "A": _snap_meta(payload_a),
            "B": _snap_meta(payload_b),
        },
        "metrics": [canonicalize_jsonish(r) for r in (metric_rows or [])],
        "state_diffs": [canonicalize_jsonish(r) for r in (state_diff_rows or [])],
    }

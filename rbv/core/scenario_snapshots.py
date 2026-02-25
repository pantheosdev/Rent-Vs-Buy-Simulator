from __future__ import annotations

from dataclasses import dataclass, field
import datetime as _dt
import hashlib
import json
import math
from typing import Any, Iterable

try:  # optional, keep module usable without numpy at import time
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover
    _np = None

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
    src = dict(state or {})
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
        object.__setattr__(self, "state", dict(self.state or {}))

    @property
    def canonical_state(self) -> dict[str, Any]:
        return canonicalize_jsonish(self.state)

    def canonical_json(self) -> str:
        return json.dumps(self.canonical_state, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def deterministic_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        state = self.canonical_state
        return {
            "schema": self.schema,
            "state": state,
            "hash": hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest(),
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
            return cls(state=dict(obj.get("state") or {}))
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
        object.__setattr__(self, "meta", dict(self.meta or {}))
        object.__setattr__(self, "slot", str(self.slot or "active"))

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
            meta=dict(obj.get("meta") or {}),
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


def parse_scenario_payload(payload: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (state, metadata) from legacy or v1 snapshot payloads."""
    snap = ScenarioSnapshot.from_payload(payload)
    meta = {
        "slot": snap.slot,
        "label": snap.label,
        "scenario_hash": snap.scenario_hash,
        "schema": snap.schema,
        "version": snap.version,
        "exported_at": snap.exported_at,
        "app": snap.app,
    }
    return dict(snap.config.canonical_state), meta

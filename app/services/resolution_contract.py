"""Strict validation and safe projection for Rule Engine resolution responses.

This contract validates data only. It does not implement or infer game rules.
"""

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationError,
)

from app.services.ux_assistant import CombatUXSnapshot, LongRestSummary

RULE_RESOLUTION_SCHEMA_VERSION = "rule-resolution-v1"

RuleResolutionStatus = Literal[
    "needs_rule_validation",
    "awaiting_input",
    "awaiting_roll",
    "resolved",
    "invalid_action",
    "rule_not_found",
]

SUPPORTED_STATUSES = frozenset(
    {
        "needs_rule_validation",
        "awaiting_input",
        "awaiting_roll",
        "resolved",
        "invalid_action",
        "rule_not_found",
    }
)

MAX_RESOLUTION_BYTES = 50_000
MAX_STATE_CHANGES = 32
MAX_RULE_REFS = 100
MAX_REFERENCE_LENGTH = 200
STATE_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")

TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "resolution_id",
        "status",
        "action",
        "request",
        "check",
        "rolls",
        "outcome",
        "facts_resolvidos",
        "FATOS_RESOLVIDOS",
        "state_changes",
        "rules_used",
        "ux_snapshot",
        "long_rest_summary",
        "reason",
        "message",
    }
)

# These fields are never authoritative when status is not "resolved".
AUTHORIZED_FIELDS = frozenset(
    {
        "outcome",
        "facts_resolvidos",
        "FATOS_RESOLVIDOS",
        "state_changes",
        "rules_used",
        "ux_snapshot",
        "long_rest_summary",
    }
)


class ResolutionContractError(ValueError):
    """The Rule Engine response does not satisfy the versioned contract."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Action(_StrictModel):
    type: StrictStr
    actor_id: StrictStr | None = None


class _Request(_StrictModel):
    player_input: StrictStr


class _Check(_StrictModel):
    ability: StrictStr | None = None
    skill: StrictStr | None = None
    dc: StrictInt | None = None
    modifier: StrictInt | None = None


class _Roll(_StrictModel):
    type: StrictStr
    result: StrictInt


class _Outcome(_StrictModel):
    success: StrictBool | None = None
    total: StrictInt | None = None


class _ResolvedFacts(_StrictModel):
    """Legacy nested FATOS_RESOLVIDOS shape accepted inside resolution v1."""

    resolution_id: StrictStr | None = None
    status: Literal["resolved"]
    action: StrictStr | None = None
    outcome: StrictStr | None = None
    rolls: list[dict[StrictStr, Any]] | None = None
    damage: dict[StrictStr, Any] | None = None
    conditions_applied: list[dict[StrictStr, Any]] | None = None
    state_changes: list[dict[StrictStr, Any]] | None = None
    rules_used: list[StrictStr] | None = None
    ux_snapshot: dict[StrictStr, Any] | None = None
    long_rest_summary: dict[StrictStr, Any] | None = None


class _RuleResolution(_StrictModel):
    schema_version: Literal["rule-resolution-v1"]
    resolution_id: StrictStr | None = None
    status: RuleResolutionStatus
    action: _Action | None = None
    request: _Request | None = None
    check: _Check | None = None
    rolls: list[_Roll] | None = None
    outcome: _Outcome | None = None
    facts_resolvidos: dict[StrictStr, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("facts_resolvidos", "FATOS_RESOLVIDOS"),
    )
    state_changes: dict[StrictStr, Any] | None = None
    rules_used: list[StrictStr] | None = None
    ux_snapshot: dict[StrictStr, Any] | None = None
    long_rest_summary: dict[StrictStr, Any] | None = None
    reason: StrictStr | None = Field(default=None, max_length=500)
    message: StrictStr | None = Field(default=None, max_length=500)


@dataclass(frozen=True)
class ValidatedResolution:
    """The authorized result of validating one upstream response."""

    status: str
    narrator_facts: dict[str, Any]
    state_changes: dict[str, Any]
    reason: str | None = None


def fail_closed_resolution() -> ValidatedResolution:
    """Return the only safe result to use when an upstream response is invalid."""
    return ValidatedResolution(
        status="needs_rule_validation",
        narrator_facts={},
        state_changes={},
    )


def _ensure_json_size(value: Any) -> None:
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ResolutionContractError(
            "resolution must contain JSON-compatible values"
        ) from exc
    if len(encoded.encode("utf-8")) > MAX_RESOLUTION_BYTES:
        raise ResolutionContractError("resolution exceeds the maximum payload size")


def _validate_scalar_changes(changes: Any) -> dict[str, Any]:
    if not isinstance(changes, dict) or len(changes) > MAX_STATE_CHANGES:
        raise ResolutionContractError("state_changes must be a bounded object")
    validated: dict[str, Any] = {}
    for key, value in changes.items():
        if not isinstance(key, str) or not STATE_KEY_RE.fullmatch(key):
            raise ResolutionContractError("state_changes contains an invalid key")
        if value is not None and type(value) not in (str, int, float, bool):
            raise ResolutionContractError("state_changes values must be JSON scalars")
        if isinstance(value, float) and not math.isfinite(value):
            raise ResolutionContractError("state_changes contains a non-finite number")
        validated[key] = value
    return validated


def _validate_legacy_changes(changes: Any) -> dict[str, Any]:
    if not isinstance(changes, list) or len(changes) > MAX_STATE_CHANGES:
        raise ResolutionContractError("nested state_changes must be a bounded list")
    mapped: dict[str, Any] = {}
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"key", "value"}:
            raise ResolutionContractError("nested state_changes entry is malformed")
        key = change["key"]
        if not isinstance(key, str) or not STATE_KEY_RE.fullmatch(key):
            raise ResolutionContractError(
                "nested state_changes contains an invalid key"
            )
        value = change["value"]
        if value is not None and type(value) not in (str, int, float, bool):
            raise ResolutionContractError(
                "nested state_changes values must be JSON scalars"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ResolutionContractError(
                "nested state_changes contains a non-finite number"
            )
        if key in mapped:
            raise ResolutionContractError(
                "nested state_changes contains a duplicate key"
            )
        mapped[key] = value
    return mapped


def _validate_snapshot(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        snapshot = CombatUXSnapshot.model_validate(value, strict=True)
    except ValidationError as exc:
        raise ResolutionContractError(
            "ux_snapshot does not satisfy the UX schema"
        ) from exc
    normalized = snapshot.model_dump(exclude_none=True, exclude_unset=True)
    _ensure_json_size(normalized)
    return normalized


def _validate_rest_summary(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        summary = LongRestSummary.model_validate(value, strict=True)
    except ValidationError as exc:
        raise ResolutionContractError(
            "long_rest_summary does not satisfy the summary schema"
        ) from exc
    normalized = summary.model_dump(exclude_none=True, exclude_unset=True)
    _ensure_json_size(normalized)
    return normalized


def _model_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True, exclude_unset=True)
    if isinstance(value, dict):
        return {key: _model_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_model_value(item) for item in value]
    return value


def _merge_fact(target: dict[str, Any], key: str, value: Any) -> None:
    value = _model_value(value)
    if key in target and target[key] != value:
        raise ResolutionContractError(f"conflicting values for resolved field: {key}")
    target[key] = value


def _validate_resolved_response(envelope: _RuleResolution) -> ValidatedResolution:
    fields_set = envelope.model_fields_set
    facts: dict[str, Any] = {
        "schema_version": RULE_RESOLUTION_SCHEMA_VERSION,
        "status": "resolved",
    }
    if "resolution_id" in fields_set and envelope.resolution_id is not None:
        facts["resolution_id"] = envelope.resolution_id

    # Player input is already sent separately to MiMo; only validated resolution
    # data, not the original request wrapper or upstream error text, is projected.
    for field in ("action", "check", "rolls", "outcome"):
        if field in fields_set and getattr(envelope, field) is not None:
            _merge_fact(facts, field, getattr(envelope, field))

    inner_facts: dict[str, Any] = {}
    nested_changes: dict[str, Any] = {}
    raw_inner = envelope.facts_resolvidos
    if raw_inner:
        try:
            inner_model = _ResolvedFacts.model_validate(raw_inner, strict=True)
        except ValidationError as exc:
            raise ResolutionContractError(
                "facts_resolvidos does not satisfy its schema"
            ) from exc
        inner_facts = inner_model.model_dump(exclude_none=True, exclude_unset=True)
        if (
            inner_model.resolution_id
            and envelope.resolution_id
            and inner_model.resolution_id != envelope.resolution_id
        ):
            raise ResolutionContractError(
                "resolution_id differs between envelope and facts"
            )
        if inner_model.state_changes is not None:
            nested_changes = _validate_legacy_changes(inner_model.state_changes)
        if inner_model.ux_snapshot is not None:
            inner_facts["ux_snapshot"] = _validate_snapshot(inner_model.ux_snapshot)
        if inner_model.long_rest_summary is not None:
            inner_facts["long_rest_summary"] = _validate_rest_summary(
                inner_model.long_rest_summary
            )
        _ensure_json_size(inner_facts)

    for key, value in inner_facts.items():
        if key in {"status", "state_changes"}:
            continue
        _merge_fact(facts, key, value)

    outer_changes: dict[str, Any] = {}
    if envelope.state_changes is not None:
        outer_changes = _validate_scalar_changes(envelope.state_changes)
    if outer_changes and nested_changes and outer_changes != nested_changes:
        raise ResolutionContractError("top-level and nested state_changes conflict")
    effective_changes = outer_changes or nested_changes
    if "state_changes" in fields_set or nested_changes:
        facts["state_changes"] = effective_changes

    if envelope.rules_used is not None:
        if len(envelope.rules_used) > MAX_RULE_REFS or any(
            not ref.strip() or len(ref) > MAX_REFERENCE_LENGTH
            for ref in envelope.rules_used
        ):
            raise ResolutionContractError("rules_used contains invalid references")
        _merge_fact(facts, "rules_used", envelope.rules_used)

    if envelope.ux_snapshot is not None:
        _merge_fact(facts, "ux_snapshot", _validate_snapshot(envelope.ux_snapshot))
    if envelope.long_rest_summary is not None:
        _merge_fact(
            facts,
            "long_rest_summary",
            _validate_rest_summary(envelope.long_rest_summary),
        )

    _ensure_json_size(facts)
    return ValidatedResolution(
        status="resolved",
        narrator_facts=facts,
        state_changes=effective_changes,
    )


def validate_resolution_response(raw: Any) -> ValidatedResolution:
    """Validate one Rule Engine response and project only authorized data.

    The only unversioned response accepted for compatibility is the current
    backend's minimal ``{"status": "needs_rule_validation"}`` form. Any
    additional legacy field is rejected; unresolved facts are never authorized.
    """
    if not isinstance(raw, dict):
        raise ResolutionContractError("resolution response must be an object")
    _ensure_json_size(raw)

    unexpected = set(raw) - TOP_LEVEL_FIELDS
    if unexpected:
        raise ResolutionContractError("resolution response contains unexpected fields")
    if "facts_resolvidos" in raw and "FATOS_RESOLVIDOS" in raw:
        raise ResolutionContractError(
            "resolution response contains duplicate facts fields"
        )

    status = raw.get("status")
    if not isinstance(status, str) or status not in SUPPORTED_STATUSES:
        raise ResolutionContractError("resolution status is unsupported")
    version = raw.get("schema_version")
    legacy_needs_validation = version is None and status == "needs_rule_validation"
    if version is not None and version != RULE_RESOLUTION_SCHEMA_VERSION:
        raise ResolutionContractError("resolution schema_version is unsupported")
    if version is None and not legacy_needs_validation:
        raise ResolutionContractError("schema_version is required")
    if legacy_needs_validation and set(raw) != {"status"}:
        raise ResolutionContractError(
            "legacy compatibility accepts only the minimal status response"
        )

    source = dict(raw)
    source["schema_version"] = RULE_RESOLUTION_SCHEMA_VERSION

    if status != "resolved":
        # Validate only non-authoritative metadata. Discard all fields that could
        # carry mechanical facts, state changes, or UX projections.
        safe_fields = TOP_LEVEL_FIELDS - AUTHORIZED_FIELDS
        safe_source = {
            key: value for key, value in source.items() if key in safe_fields
        }
        try:
            envelope = _RuleResolution.model_validate(safe_source, strict=True)
        except ValidationError as exc:
            raise ResolutionContractError(
                "unresolved response has invalid metadata"
            ) from exc
        return ValidatedResolution(
            status=envelope.status,
            narrator_facts={},
            state_changes={},
            reason=envelope.reason or envelope.message,
        )

    try:
        envelope = _RuleResolution.model_validate(source, strict=True)
    except ValidationError as exc:
        raise ResolutionContractError(
            "resolved response does not satisfy rule-resolution-v1"
        ) from exc
    return _validate_resolved_response(envelope)

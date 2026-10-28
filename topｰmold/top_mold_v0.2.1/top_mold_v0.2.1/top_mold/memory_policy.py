"""Conservative reference rules for Top Mold v0.2.1 information lifecycle.

This module is a small policy helper, not a database, privacy-compliance engine,
identity resolver, or automatic conversation-ingestion system.
"""
from __future__ import annotations

from math import isfinite, pow
from typing import Optional

# Active-priority half-lives are examples and should be tuned only after testing.
# None means time alone does not lower priority; the record can still be revised.
DEFAULT_HALF_LIVES = {
    "transient": 1.0,
    "temporary_context": 3.0,
    "task_state": 7.0,
    "external_fact": 14.0,
    "observed_hypothesis": 30.0,
    "interaction_preference": 45.0,
    "explicit_preference": None,
    "manual_setting": None,
}

TRANSIENT_LABELS = {"transient", "joke", "banter", "one_off_topic", "temporary_context"}
def persistence_decision(
    record_type: str,
    *,
    explicit_permission: bool = False,
    explicit_durable_preference: bool = False,
    sensitive: bool = False,
    clear_purpose: bool = False,
    evidence_count: int = 1,
    independent_context_count: int = 0,
    task_active: bool = False,
    user_deletion_requested: bool = False,
    source_available: bool = False,
    validity_known: bool = False,
) -> str:
    """Return a reviewable retention decision without writing any data.

    A count of repeated mentions is not enough by itself to support a durable
    hypothesis: observations must span independent contexts. Sensitive inferred
    traits are not persisted, even when repeated. Explicit permission for storing
    sensitive information is necessary but not sufficient without a clear purpose.
    """
    if not isinstance(record_type, str) or not record_type:
        raise TypeError("record_type must be a non-empty string")
    boolean_values = {
        "explicit_permission": explicit_permission,
        "explicit_durable_preference": explicit_durable_preference,
        "sensitive": sensitive,
        "clear_purpose": clear_purpose,
        "task_active": task_active,
        "user_deletion_requested": user_deletion_requested,
        "source_available": source_available,
        "validity_known": validity_known,
    }
    for name, value in boolean_values.items():
        if not isinstance(value, bool):
            raise TypeError(f"{name} must be bool")
    for name, value in (("evidence_count", evidence_count), ("independent_context_count", independent_context_count)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be a non-negative integer")
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
    if independent_context_count > evidence_count:
        raise ValueError("independent_context_count cannot exceed evidence_count")

    # Deletion must win over all retention, archive, and classification paths.
    if user_deletion_requested:
        return "delete_active_and_archived_copies"

    # Sensitive inferred traits are prohibited from persistence by this helper.
    if record_type == "observed_hypothesis" and sensitive:
        return "do_not_persist_sensitive_inference"
    if sensitive and not explicit_permission:
        return "do_not_persist_without_explicit_permission"
    if sensitive and not clear_purpose:
        return "do_not_persist_without_clear_purpose"

    if record_type in TRANSIENT_LABELS:
        return "session_only"
    if record_type == "task_state":
        return "active_task_state" if task_active else "inactive_task_state_review_or_expire"
    if record_type in {"explicit_preference", "interaction_preference", "manual_setting"}:
        if explicit_durable_preference or explicit_permission:
            return "durable_profile_candidate"
        return "ask_or_wait_for_confirmation"
    if record_type == "observed_hypothesis":
        if evidence_count < 3:
            return "session_only_insufficient_repeated_evidence"
        if independent_context_count < 2:
            return "scoped_hypothesis_needs_independent_context_review"
        return "scoped_hypothesis_candidate_for_review"
    if record_type == "external_fact":
        if not source_available:
            return "do_not_treat_as_verified_external_fact"
        if not validity_known:
            return "needs_timestamp_or_validity_review"
        return "retain_with_source_and_revalidation_date"
    if record_type == "temporary_context":
        return "session_only"
    return "needs_classification_review"


def decay_weight(
    record_type: str,
    age_days: float,
    half_life_days: Optional[float] = None,
) -> float:
    """Return an active-priority weight in [0, 1], not a deletion decision.

    Unknown types use a conservative 30-day half-life. Durable preferences and
    manual settings do not decay from time alone unless an override half-life
    is explicitly supplied. Non-finite numeric values are rejected.
    """
    if isinstance(age_days, bool) or not isinstance(age_days, (int, float)):
        raise TypeError("age_days must be a non-negative finite number")
    try:
        numeric_age = float(age_days)
    except (OverflowError, ValueError):
        raise ValueError("age_days must be finite") from None
    if not isfinite(numeric_age):
        raise ValueError("age_days must be finite")
    if age_days < 0:
        raise ValueError("age_days must be non-negative")
    if not isinstance(record_type, str) or not record_type:
        raise TypeError("record_type must be a non-empty string")

    if half_life_days is None:
        if record_type in DEFAULT_HALF_LIVES:
            half_life_days = DEFAULT_HALF_LIVES[record_type]
        else:
            half_life_days = 30.0
    if half_life_days is None:
        return 1.0
    if isinstance(half_life_days, bool) or not isinstance(half_life_days, (int, float)):
        raise TypeError("half_life_days must be a positive finite number or None")
    try:
        numeric_half_life = float(half_life_days)
    except (OverflowError, ValueError):
        raise ValueError("half_life_days must be finite") from None
    if not isfinite(numeric_half_life):
        raise ValueError("half_life_days must be finite")
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")

    ratio = numeric_age / numeric_half_life
    if not isfinite(ratio):
        return 0.0
    weight = pow(0.5, ratio)
    return min(1.0, max(0.0, weight))

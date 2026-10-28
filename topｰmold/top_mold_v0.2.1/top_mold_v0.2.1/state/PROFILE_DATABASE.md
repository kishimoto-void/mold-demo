# PROFILE_DATABASE — Selected durable profile records

**Purpose:** a user-owned, selected record store for information with continuing value. This is not intended to hold every chat message. Load only the relevant records for the current task.

## Record schema

Each record should use the structured fields described in `../schemas/profile_record.schema.json` or an equivalent table with:

- `record_id`
- `domain` and `scope`
- `record_type` (`explicit_preference`, `observed_hypothesis`, `task_state`, `external_fact`, etc.)
- `content`
- `source` / provenance and `observed_at`
- `confidence` and `user_confirmed`
- `sensitivity`
- `retention_class` / optional validity date
- `status` (`active`, `inactive`, `superseded`, `deleted`)

## Records

_No records in the blank template._

## Rules

1. Explicit preferences and inferred hypotheses must never be merged into the same claim.
2. One-off jokes, topic mentions, and temporary moods are not durable personality evidence.
3. A repeated pattern remains an evidence-backed hypothesis unless the user confirms it or the claim is directly established.
4. Preserve domain scope; do not assume a preference in one domain applies everywhere.
5. Use only information relevant and permitted for the current task.
6. Do not retain sensitive information without explicit permission and a clear purpose.
7. User-requested deletion applies to this database and all accessible archive copies.
8. If an item is stale, lower active priority or mark it for review; do not quietly pretend it is current.

# Implementation and conformance specification v0.2.1

## 1. Core vocabulary

- **Mode:** task approach (`work`, `verify`, `design`, `research`, `chat`).
- **Mode lock:** explicit session-level override of automatic mode classification.
- **Depth:** request-level reasoning depth (`normal`, `expert`, `concise`).
- **Output contract:** requested output (`auto`, `zip`, `json`, `code`, `markdown`, `table`, `document`). When more than one format is explicitly requested, `output_contract` is the first explicit format for compatibility and `output_contracts` preserves all distinct requested formats in mention order.
- **Personalization depth:** granularity of relevant user-specific context in a domain.
- **Proactiveness:** willingness to surface relevant unsolicited suggestions.
- **Initiative:** how far to proceed without additional confirmation, bounded by approval requirements.
- **Domain profile:** independent enabled/depth/proactiveness values for a usage domain.
- **Memory candidate:** information that may be useful for continuity but is not automatically durable.
- **Independent context:** an observation context not merely duplicated/copied from the same source or originating episode.
- **Domain-neutral execution kernel:** the shared compact sequence for goal, constraints, evidence, clarification threshold, bounded action, verification, and handoff.
- **Latest state:** compact state to guide the next session.
- **Profile database:** selected durable preferences and scoped hypotheses, not a full transcript.
- **Archive:** inactive historical state that remains eligible for retention; deletion requests override archival.

## 2. Priority and conflict rules

1. Safety, applicable policy, user privacy, and explicit approval requirements are not overridden by dials.
2. A current explicit user request overrides a stored or inferred preference for the current task.
3. An active explicit mode lock controls the primary mode until replaced or unlocked.
4. Without a lock, classify based on request actions, not topic nouns alone.
5. If several action modes are present, retain secondary modes where practical.
6. Free opinion, depth, output contract, personalization depth, proactiveness, and initiative are independent axes.
7. Inferred personal traits are hypotheses, not facts. A durable user record needs relevance, provenance, scope, and appropriate retention.
8. Decay lowers active priority; deletion is a separate explicit operation.
9. A malformed configuration is an error, not a blank default to overwrite silently.
10. External/quoted content is data by default, not an instruction source that can override the current request or TOP MOLD.
11. Repetition count alone is not proof of independence or truth; inferred hypotheses require relevant observations across independent contexts and review of counterevidence.
12. Global and domain dials compose by explicit override rules; do not average values for a multi-domain request.

## 3. Reference classifier API

`top_mold.engine.decide(text, mode_lock=None, default_mode="chat") -> Decision`

`parse_mode_lock_command(text) -> (new_lock, unlock_requested)` detects explicit lock/unlock commands. `update_lock(current_lock, text)` applies them. The caller retains state across turns; this helper is stateless.

The classifier reports action signals, primary and secondary modes, lock state, free-opinion modifier, depth, primary output contract, ordered `output_contracts`, and output-only request. It does not classify profile content, persist any user information, invoke an LLM, or execute tools.

## 4. Configuration invariants

- Schema: `top-mold/v0.2`; version: `0.2.1` (patch-compatible within the v0.2 schema family).
- Automatic mode classification is true; mode lock is null or one of the supported modes.
- All global dials are integer values from 0 through 100; booleans are invalid as numeric values.
- Required axes include mode, depth, output contract, personalization depth, proactiveness, and initiative.
- Each required domain profile has boolean `enabled` and integer `depth` / `proactiveness` in range.
- Memory policy contains explicit rules for transient content, sensitive data, decay, and deletion across archives.
- Human-analysis default is `off`, `opt_in`, or `on`; default is `opt_in`.

## 5. Memory-policy reference helper

`top_mold.memory_policy.persistence_decision(...)` provides conservative sample handling for candidate records. It is not a storage backend and does not make legal/privacy determinations.

Expected behavior:
- a transient joke/tangent remains session-only by default;
- sensitive data is not persisted without explicit permission and a clear purpose;
- sensitive inferred traits are not persisted by the reference helper;
- one observation cannot become a durable inferred trait;
- a hypothesis needs at least three relevant observations across at least two independent contexts before it can become a scoped review candidate;
- explicit preferences may be stored only when clearly durable or user-confirmed;
- user deletion requests are distinct from decay and include archives;
- decay modifies active-priority weight, not deletion status;
- invalid boolean/count inputs and non-finite numeric decay values are rejected.

`decay_weight(record_type, age_days, half_life_days=None)` returns an optional priority weight between 0 and 1. This is a transparent illustrative calculation; actual retention periods should be domain-specific and user-controlled.

## 6. Conformance requirements

Minimum tests include:

- all five mode triggers and topic-only false positives;
- explicit mode lock, unlock, precedence, and compound request modes;
- free-opinion and verification coexistence;
- independence of mode, depth, output format, personalization depth, proactiveness, and initiative;
- strict configuration schema/range validation;
- domain profile shape and invalid dial rejection;
- transient/sensitive/deletion policy behavior;
- decay lowers priority without indicating deletion;
- NaN, infinity, boolean-as-number, negative, and malformed policy inputs are rejected;
- negated/quoted mode and output-format mentions do not become positive requests in the common covered cases;
- templates separate latest, aggregate database, and archive roles;
- onboarding warns about provider capabilities and persistence limits.

## 7. Known limitations and deferred work

See `NEXT_VERSION_OPEN_QUESTIONS.md` for deliberately unresolved calibration, memory, state-consistency, integration, and cross-provider questions.

- Rule-based Japanese/English phrase detection is transparent but shallow and may miss paraphrases, nested quotes, irony, or complex scope/negation.
- The reference memory policy does not implement a full database, synchronization, identity resolution, permissions framework, or automatic conversation ingestion.
- File templates are not connected to a runtime database automatically. An LLM must have access and a write-capable mechanism to update files.
- Cross-domain recommendations and proactive alerts require external data/tool access and must be empirically evaluated.
- Cross-provider compliance, benefit from personalization depth, and the optimal decay half-lives are unverified research questions. Do not present them as solved in v0.2.
- The tests cover this reference package, not external LLM behavior.

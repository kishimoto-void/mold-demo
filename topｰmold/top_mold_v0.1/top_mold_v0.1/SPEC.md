# Implementation and conformance specification v0.1

## 1. Core vocabulary

- **Mode:** primary task approach (`work`, `verify`, `design`, `research`, `chat`).
- **Secondary mode:** additional detected task that should be preserved where practical.
- **Mode lock:** explicit session-level override of automatic mode classification.
- **Free-opinion modifier:** request to explore opinions and hypotheses more freely; not a mode and not a permission to mislabel facts.
- **Depth:** `normal`, `expert`, or `concise`.
- **Output contract:** `auto`, `zip`, `json`, `code`, `markdown`, `table`, or `document`.
- **Output-only:** request to return only the requested deliverable without extra explanation.

## 2. Priority rules

1. Active explicit mode lock controls the primary mode.
2. Without a lock, classify based on requested action signals, not topic nouns alone.
3. If multiple action modes are present, preserve secondary modes. The reference implementation uses the earliest clear action signal as primary, then retains other detected modes as secondary; ties use signal strength. This is a convenience heuristic, not a universal linguistic rule.
4. Free opinion, depth, and output contract are independent of primary mode.
5. A verification request remains evidence-conscious even when free-opinion is also requested.
6. Safety and truthful reporting are not disabled by mode, persona, or dials.

## 3. Reference implementation API

`top_mold.engine.decide(text, mode_lock=None, default_mode="chat") -> Decision`

The returned decision includes primary mode, secondary modes, lock state, free-opinion flag, depth, output contract, output-only flag, matched mode signals, and explanatory notes.

`parse_mode_lock_command(text) -> (new_lock, unlock_requested)` detects explicit commands. `update_lock(current_lock, text)` applies those commands. The caller is responsible for retaining `current_lock` across turns; the engine itself is stateless.

## 4. Required config invariants

- Schema exactly `top-mold/v0.1`.
- Automatic classification enabled.
- Mode lock is null or one of the five supported modes.
- Every dial is an integer 0–100 (booleans are invalid even though Python treats them as integers).
- Mode, depth, and output contract are present as independent axes.
- Human analysis default is `off`, `opt_in`, or `on`.

## 5. Conformance expectations

Any implementation derived from this package should pass at minimum:

- Mode intent tests for all five modes.
- Topic-only false-positive tests.
- Explicit lock/unlock and lock-precedence tests.
- Combined work+verification tests.
- Free-opinion + verification coexistence tests.
- Depth/output orthogonality tests.
- Config schema/range validation tests.
- Honest test-reporting and unknown-preservation checks in the normative contract.

## 6. Known limitations

The rule-based classifier is deterministic but shallow. It does not solve ambiguity, infer the full semantics of a conversation, or inspect model output. A provider-specific or LLM-driven implementation may improve intent recognition but must retain explainability, mode-lock semantics, and the above conformance cases.

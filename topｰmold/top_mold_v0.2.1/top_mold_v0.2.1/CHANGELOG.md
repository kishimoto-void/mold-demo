# Changelog

## 0.2.1 — Micro-hardening and cross-domain consistency

- Added a domain-neutral execution kernel for goals, constraints/exclusions, evidence state, clarification thresholds, bounded action, proportional verification, and handoff.
- Defined all global dial meanings as heuristics and clarified enabled/disabled/unknown-domain override behavior without averaging dials.
- Separated external content from instruction authority; quoted/source content is treated as data by default.
- Hardened common Japanese/English mode and output-format detection against quoted actions, local negations, and format mentions that are not deliverable requests.
- Made output-format choice depend on the earliest explicit positive request rather than a fixed format priority.
- Tightened configuration validation for version, mode list, scale value types, and malformed human-analysis settings.
- Added finite numeric validation for decay, strict policy argument validation, a clear-purpose gate for sensitive storage, and an independent-context gate for hypothesis candidates.
- Aligned profile-record schema and tests with the expanded transient record vocabulary and independence requirement.
- Kept dial calibration and cross-provider behavior explicitly unvalidated; no production or universal compliance claim is made.

## 0.2.0 — Domain-aware personalization and state lifecycle

- Reframed Top Mold explicitly as an LLM-facing control layer; Markdown is the portable instruction/state medium, not a human-first UI.
- Separated personalization depth, proactiveness, initiative, retention preference, and domain-specific depth.
- Added domain profiles for general, shopping, learning, development, events/entertainment, and daily life.
- Added personal-hub guidance for permitted cross-source and cross-domain information reuse without requiring all data to be centralized.
- Added conservative memory lifecycle rules: session-only transient content, evidence-scoped hypotheses, sensitivity boundaries, priority decay vs deletion, and deletion across archives.
- Added distinct latest-state, profile-database, and archive templates plus a checkpoint-based MD update protocol.
- Made prompt generation optional/on-demand and documented integration, persistence, and provider-capability limits.
- Added reference memory-policy helpers and tests.
- Preserved the v0.1 mode classifier, independent task modes, explicit mode lock, and verification integrity rules.
- Added `NEXT_VERSION_OPEN_QUESTIONS.md` to carry unresolved calibration, decay, synchronization, integration, and cross-provider questions forward.
- Deferred empirical validation of cross-provider behavior, personalization benefit, and domain-specific forgetting curves.

## 0.1.0 — Initial tested skeleton

- Added portable TOP behavior contract and LLM onboarding instructions.
- Added automatic task-mode classification with explicit lock/unlock semantics.
- Kept task mode, reasoning depth, and output contract independent.
- Added free-opinion modifier that does not erase verification discipline.
- Added model-neutral JSON dials and opt-in human analysis.
- Added local reference engine and automated unit/conformance tests.

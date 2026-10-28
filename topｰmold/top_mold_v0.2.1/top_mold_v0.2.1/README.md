# Top Mold v0.2.1 — Portable personal LLM control layer

**Status:** experimental prototype. This patch hardens small-context interpretation, clarifies cross-domain dial composition, adds a domain-neutral execution kernel, and tightens evidence/retention validation without claiming empirical cross-provider guarantees. Cross-provider behavior is not guaranteed.

Top Mold is designed for an LLM to read and follow. The user can speak naturally and ask the LLM to explain, adjust, or update the Markdown state. The package itself is not a shopping application, calendar service, database host, or autonomous agent.

## Included

- `TOP_MOLD.md` — normative behavior contract.
- `LLM_README.md` — startup, use, and state update instructions for an LLM.
- `SPEC.md` — reference implementation and conformance rules.
- `config/top_mold.json` — global dials, independent domain profiles, memory/data/access rules.
- `top_mold/engine.py` — deterministic heuristic classifier for task mode, depth, explicit output contracts (including multiple requested formats), and explicit mode locks.
- `top_mold/memory_policy.py` — conservative reference helper with sensitive-data purpose gates, independent-context checks, strict input validation, and priority decay.
- `state/` — starter templates for latest state, profile database, archive, and MD update protocol.
- `schemas/profile_record.schema.json` — suggested record structure.
- `examples/` — generic sample configuration; contains no real user profile.
- `tests/` — unit, policy, boundary, contract, and conformance tests.
- `TEST_REPORT.md` — results from tests actually run for this ZIP.
- `CHANGELOG.md` — changes from v0.1.0.
- `NEXT_VERSION_OPEN_QUESTIONS.md` — deliberately unresolved design questions carried forward.

## Quick start

No third-party Python dependencies are required. From this directory:

```bash
python -m unittest discover -s tests -v
python -m compileall -q top_mold tests
python -m json.tool config/top_mold.json
```

Try the reference classifier:

```bash
python -m top_mold.engine "トップモールドを作成して、厳密にテストして"
python -m top_mold.engine --json "ChatGPT的にどう思う？ これをZIPにして"
python -m top_mold.engine --lock design "テストして"
```

The engine shows how these simple reference rules classify a request. It does **not** control ChatGPT, Claude, Gemini, Grok, or any other LLM by itself.

## Quick personalization

Edit `config/top_mold.json` or ask an LLM that can access the files to help update it. The 0–100 values are heuristic preferences, not calibrated probabilities or linear measurements. Personalization depth and proactiveness are intentionally independent. Each enabled domain profile overrides those two values for its domain; do not average values across domains.

- Low setup first: start with defaults and ordinary conversation.
- Increase domain depth only when more detailed personalization is useful.
- Increase proactiveness when you want more relevant early suggestions; lower it when the LLM overreaches.
- Prompt generation is opt-in/on-demand; it is not a required step for ordinary tasks.
- Settings are guidance, not proof of equal behavior across providers.

## State files

- `state/LATEST.md`: compact active settings/state for the next session.
- `state/PROFILE_DATABASE.md`: selected durable preferences and scoped hypotheses.
- `state/ARCHIVE.md`: inactive historical state; not always loaded.
- `state/UPDATE_PROTOCOL.md`: how to update at user-requested or natural checkpoints.

The files are templates. They do not sync themselves with ChatGPT memory, other LLMs, calendars, purchase histories, or external services. Keep only relevant, permitted information, and never use an archive to bypass a deletion request.

## Versioning

See `CHANGELOG.md`. v0.2.1 is a compatibility-minded hardening patch in the v0.2 line, not a production-ready implementation of the full concierge vision. It does not change the schema family (`top-mold/v0.2`).

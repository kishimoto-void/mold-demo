# Top Mold v0.1 — Portable personal AI control interface

**Status:** experimental prototype. The reference classifier is rule-based and deliberately small; cross-model behavior is not yet proven.

Top Mold is the simple front door: most users should be able to personalize an AI without learning the mold architecture. If repeated needs appear, the user can ask an LLM to convert them into a reusable MIDDLE mold. If the underlying procedure itself needs changing, the user can later inspect or build a BOTTOM mold.

## Included

- `TOP_MOLD.md` — normative behavior contract.
- `LLM_README.md` — instructions for another LLM to read, personalize, test, and package this mold.
- `config/top_mold.json` — portable settings and dials.
- `top_mold/engine.py` — deterministic reference classifier for task mode, depth, output contract, and lock signals.
- `tests/` — unit, boundary, contract, and conformance tests.
- `examples/` — small sample profile.
- `TEST_REPORT.md` — test result generated for this package.

## Quick start

No third-party dependencies are required. From this directory, run:

```bash
python -m unittest discover -s tests -v
```

Try the reference classifier:

```bash
python -m top_mold.engine "トップモールドを作成して、厳密にテストして"
python -m top_mold.engine --json "ChatGPT的にどう思う？ これをZIPにして"
python -m top_mold.engine --lock design "テストして"
```

The engine only explains how the reference rules classify a request. It does **not** control ChatGPT, Gemini, Grok, or any other LLM by itself. To use the behavior contract, upload/share the package with a target LLM and tell it to read `LLM_README.md` and `TOP_MOLD.md`.

## Quick personalization

Edit `config/top_mold.json`. Dial values are 0–100; higher means more of the named behavior. The defaults intentionally favor user agency and verification, with moderate proactiveness and low-to-moderate generalization. Human-analysis mode is opt-in by default.

| Dial | What a higher value means |
|---|---|
| `proactiveness` | More suggestions about dependencies, tests, next steps |
| `generalization` | More abstraction and transfer to broader principles |
| `verification_strictness` | More explicit checks, evidence labels, edge cases |
| `drift_allowance` | More exploratory branching and creative tangents when invited |
| `detail_structure` | More hierarchy, explicit sections, and structured outputs |
| `concision` | More compression and less elaboration |
| `user_agency` | More user choice and fewer unilateral decisions |
| `speculation_tolerance` | More hypotheses, always labeled as hypotheses |

These dials can conflict. If they do, preserve explicit user instructions and do not silently suppress uncertainty. For instance, a high drift allowance does not justify inventing facts during verification.

## Design decisions

- TOP is useful on its own; MIDDLE/BOTTOM are optional.
- Task mode, depth, and output contract are separate axes.
- Automatic task classification is enabled; an explicit lock takes priority until replaced or unlocked.
- Free-opinion mode broadens exploration but does not cancel verification discipline.
- A shared skeleton should be modifiable and inheritable rather than treated as an immutable standard.
- The package documents assumptions and tests so another person can adapt it without relying on the original author's presence.

## Limits

- Rule-based Japanese/English phrase detection is not semantic understanding. It can miss paraphrases or detect overlapping signals.
- The Python tests verify the reference engine and artifact structure, not an external LLM's obedience.
- Portability is a design goal, not a guarantee of identical behavior across models.
- No mold alone can guarantee safety, prevent misuse, or establish responsibility for an external event.

## Versioning

See `CHANGELOG.md`. This is v0.1.0: a tested skeleton meant for critique and iteration, not a claim of production readiness.

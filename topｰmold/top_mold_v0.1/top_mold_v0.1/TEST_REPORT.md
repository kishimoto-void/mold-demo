# Test Report — Top Mold v0.1.0

**Result: PASS** for the bundled reference implementation and package-level contract checks.

- Runtime: Python 3.13.5
- Third-party dependencies: none
- Automated test methods: 43 passed, 0 failed
- Golden conformance cases: 15 cases exercised through the conformance test
- Additional checks: Python byte-compilation passed; `config/top_mold.json` parsed and validated; `tests/conformance_cases.json` parsed; CLI smoke test passed.

## Test areas

1. Five mode triggers: work, verify, design, research, chat.
2. Topic-only false positives for words such as “test”, “design”, and “research”.
3. Compound actions preserve secondary tasks and use the earliest clear action as primary.
4. Explicit lock, lock precedence, replacing a lock, and unlocking.
5. Free-opinion modifier coexists with verification discipline.
6. Mode, depth, and output contract remain independent.
7. Japanese ZIP/output-only phrasing, including ASCII terms adjacent to Japanese characters.
8. Config schema, supported lock values, required axes, opt-in human analysis, dial type/range validation.
9. Empty input, invalid input type, JSON serializability, and closed mode set.
10. Normative contract checks for human dignity, provenance, portability, pay-forward intent, and responsibility boundaries.

## Reproduction

From this directory:

```bash
python -m unittest discover -s tests -v
python -m compileall -q top_mold tests
python -m json.tool config/top_mold.json
python -m json.tool tests/conformance_cases.json
```

## Important limits

This report does **not** claim that an external LLM obeys the mold. Tests exercise the deterministic Python reference classifier, validate the bundle's normative contract, and confirm the local package's syntax/configuration. Cross-provider behavior, natural-language paraphrase coverage, long-run personalization, GUI/avatar integration, and misuse resistance have not been tested here.

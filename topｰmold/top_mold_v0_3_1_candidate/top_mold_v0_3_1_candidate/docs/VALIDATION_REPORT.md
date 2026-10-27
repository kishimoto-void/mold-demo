# Validation Report — Top Mold v0.3.1 Candidate

- **Package:** `top_mold_v0_3_1_candidate`
- **Target:** Python 3.10+; standard library only
- **Test runtime:** Python 3.13.5 (container runtime)
- **Execution boundary:** plan-only
- **Validation method:** local `unittest`, CLI smoke checks, compile check
- **Status:** candidate; not committed to upstream GitHub repository

## Test results

Command:

```bash
python -m unittest discover -s tests -v
```

Final local run: **92 tests passed, 0 failures, 0 errors**.

Coverage categories:

- Intake packet fields, duplicate IDs, confidence bounds, decision consistency, and READY-only conversion
- Deterministic route selection, compatible type chain, backtracking from a high-priority dead end, and final output contract
- Missing providers, incompatible types, disabled processors, forbidden mode, empty allow-list and missing approval
- Unknown mandatory constraints block `COMPLETE`; unknown soft constraints are still surfaced
- Dial catalog/default count, range checking, unknown ID preservation, complexity advice, overlay declaration and save/load behavior
- Corrupt settings are not replaced, and planning is independent of optional personalization settings
- Startup states (`ABSENT`, `PRESENT`, `EMPTY`, `ERROR`), invalid UTF-8, CLI operation conflicts, and the five demos
- Result Envelope status consistency, duplicate check IDs, expected task identity, and no false semantic-correctness claim
- Trace privacy defaults, explicit-only request fingerprints, task/plan identity, status consistency and CLI integration
- Registry schema/metadata validation, approval precedence, bounded route search and route-depth guard, empty allow-list consistency and mandatory-constraint classification
- One-time interactive setup, non-interactive no-prompt/no-write behavior, dangling symlink safety and repeatable, side-effect-free demo behavior
- Canonicalized dial IDs, malformed settings keys, atomic-save path errors, settings symlink protection and intake-level duplicate/known-constraint checks

## Smoke-check results

The following smoke checks were executed successfully (exit code `0` for each expected-success command):

```bash
python -m compileall -q .
python main.py --task config/task.example.json
python main.py --intake config/intake.example.json
python main.py --demo DEMO-005
python main.py --show-overlay
python main.py --result config/result.not_executed.example.json --expected-task-id TASK-EXAMPLE-001
python main.py --task config/task.example.json > /tmp/top-mold-plan.json
python main.py --trace config/task.example.json /tmp/top-mold-plan.json
python main.py --trace config/task.example.json /tmp/top-mold-plan.json --fingerprint-request
python main.py --demo DEMO-005 --task config/task.example.json  # expected argparse rejection (exit 2)
```

Observed: all 9 CLI smoke checks passed, including `--task`, `--intake`, `DEMO-005`, overlay generation, Result Envelope validation, trace generation with raw request omitted, opt-in fingerprinting, non-interactive startup without default-file writes, and rejection of conflicting operation flags. Planning outputs retained `execution_status=NOT_INVOKED` and `execution_invoked=false`. The compile check and all 92 unit tests passed. Additional tests simulate the first interactive run and confirm that the dial screen is not repeated after settings are saved.

Successful plan output must include:

```json
{
  "plan_status": "COMPLETE",
  "plan_mode": "PLAN_ONLY",
  "execution_status": "NOT_INVOKED",
  "execution_invoked": false
}
```

A complete plan means only that the declared processor capabilities, type transitions, policy filters, and required output types are covered by the registry. It does not validate the factual correctness or quality of a future LLM response.

## Test-discovery notes

The candidate suite uses `unittest` and does not install third-party packages. The argparse conflict tests capture expected parser diagnostics while asserting that `SystemExit` is raised.

## Not tested / not implemented

- Direct execution of the upstream `top_mold_skeleton_v0.3.0.zip` suite
- Actual calls to ChatGPT, Gemini, Grok, other LLMs, network APIs or external tools
- Adapter authentication and runtime permission enforcement
- Semantic verification of an LLM response or its sources
- End-to-end UI / smartphone / PC behavior
- Long-running state persistence, database-backed traces, retries, timeout and rate limiting
- Formal security audit or production-readiness review

## Version decision

Use `0.3.1-draft` as a **candidate hardening iteration**, not as a claim of official upstream release. Promote only after the user chooses whether to merge this candidate into the upstream ZIP/source tree and after reviewing the compatibility differences.

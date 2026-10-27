# Top Mold — Universal Control Skeleton

**Candidate:** `0.3.1-draft`  
**Runtime:** Python 3.10+ / standard library only  
**Status:** local reference prototype; no LLM/API/tool is executed

Top Mold is a reusable control layer for structuring a request, checking declared constraints, planning compatible processing steps, and making gaps visible. It is not a single all-purpose reasoning circuit and does not assume that a particular LLM, device, domain, or API is always available.

> This folder is a tested refinement candidate built from the visible v0.3.0 specification and CLI contract. It is not a direct commit or a verified extraction of the upstream ZIP archive. The upstream repository currently exposes the full v0.3.0 bundle as a ZIP; its internal modules and tests were not available for direct execution in this environment. See `docs/UPSTREAM_AUDIT.md`.

## Quick start

From this folder, using Python 3.10 or newer. On the first interactive terminal launch, the tool offers Persona setup and shows the eight base dials once; settings are saved after that first setup. Later ordinary launches do not repeat the dial screen. Use `--configure` to reopen settings. Non-interactive invocations never wait for input and do not write default settings as a side effect.

```bash
# First launch in an interactive terminal: one-time setup wizard
python main.py

# Run all tests
python -m unittest discover -s tests -v

# Check a Task Envelope and generate a deterministic plan
python main.py --task config/task.example.json

# Validate a structured Request Intake Packet, then plan only if READY
python main.py --intake config/intake.example.json

# Run one of the five demos
python main.py --demo DEMO-005

# Validate a future/fixture Result Envelope without claiming semantic truth
python main.py --result config/result.not_executed.example.json --expected-task-id TASK-EXAMPLE-001

# Build a trace record from a task and its saved plan (raw request omitted)
python main.py --task config/task.example.json > /tmp/top-mold-plan.json
python main.py --trace config/task.example.json /tmp/top-mold-plan.json

# Optional: include a linkable SHA-256 fingerprint only when needed
python main.py --trace config/task.example.json /tmp/top-mold-plan.json --fingerprint-request

# Print a declarative Persona Seed + Dial overlay
python main.py --show-overlay

# Open the dial configuration prompt (writes only after explicit y confirmation)
python main.py --configure
python main.py --configure --advanced-dials
```

The planner does not call processors. A `COMPLETE` plan means the declared capability sequence and output types are covered by registry declarations; it does **not** mean that a task was executed or that its semantic result is correct.

## Architecture

```text
Raw Request
  ↓  (interpretation is a pluggable external concern)
Structured Intake Packet
  ↓  validate contract and decision consistency
Task Envelope + explicit policy
  ↓
Processor Registry → deterministic capability/type route planner
  ↓  (plan only; no processor invocation)
Plan Result + diagnostics

Cross-cutting optional overlay: Persona Seed / Dials / Session Overrides
Cross-cutting record target: versions / route / status / evidence / unknowns
```

## Main files

| Path | Purpose |
|---|---|
| `core/intake.py` | Validates the structured intake contract; blocks contradictory `READY` packets |
| `core/planner.py` | Deterministic compatible route search, policy checks and partial-plan diagnostics |
| `core/registry.py` | Validates Processor and Mold registries; rejects duplicate IDs |
| `core/result_contract.py` | Checks status/outputs/verification consistency in a Result Envelope; not semantic fact-checking |
| `core/trace.py` | Builds an in-memory, privacy-minimizing trace record; does not persist or send it |
| `core/personalization.py` | Dial validation, atomic settings writes and declarative overlay construction |
| `core/startup.py` | Read-only `ABSENT / PRESENT / EMPTY / ERROR` file-state inspection |
| `main.py` | Mutually exclusive CLI operations and readable error boundary |
| `config/` | Small illustrative contracts and registry definitions |
| `tests/` | Standard-library `unittest` regression suite |
| `docs/TOP_MOLD_SKELETON.md` | Normative-ish v0.3.1 candidate specification |
| `docs/VALIDATION_REPORT.md` | Local test results and scope limits |
| `docs/UPSTREAM_AUDIT.md` | Static audit of the visible upstream v0.3.0 files |

## Status meanings

- Intake decision: `READY`, `CLARIFICATION_REQUIRED`, or `BLOCKED`.
- Plan status: `COMPLETE`, `PARTIAL`, or `BLOCKED`.
- Execution status in this prototype: always `NOT_INVOKED`.
- `COMPLETE` refers to declared contracts and registry metadata only.

## Safety and privacy boundaries

- A Persona Seed and dials describe presentation preferences. They do not grant capabilities, prove facts, or override task contracts and hard policy.
- An explicit `approval_required=true` with no recorded approval blocks route planning.
- Forbidden execution modes are excluded. An explicit empty `allowed_execution_modes` list means no mode is allowed.
- Unknown mandatory constraints prevent a plan from being labelled complete. Unknown soft constraints remain visible in diagnostics.
- Existing malformed settings are reported rather than silently replaced by defaults.
- Settings are written via a temporary file and atomic replacement after validation; a setting change is persisted only after confirmation in the CLI.
- The example Persona Seed and request packet are test data. Do not put passwords, API keys, access tokens, or unnecessary identifying details into profile or intake files.
- The Result Envelope validator checks claims for internal consistency only. `semantic_correctness` remains `NOT_ASSESSED`.
- Trace records omit raw request text by default. A SHA-256 fingerprint is opt-in and can still be linkable; traces are printed, not persisted or sent.
- Adapter authentication, permission enforcement, API execution, timeout/retry policy, semantic result verification, and cross-device tests are outside this prototype.

## Design rule

Add a capability only when its owner, input/output contract, failure modes, and regression tests can be named. Keep domain-specific reasoning, model-specific prompts, APIs, UI and persistent stores outside the generic Top Mold core.

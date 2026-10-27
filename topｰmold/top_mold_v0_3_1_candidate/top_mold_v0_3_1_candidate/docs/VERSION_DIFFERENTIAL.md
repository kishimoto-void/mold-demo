# Top Mold Version Differential — v0.1 to v0.3.1 candidate

This matrix compares the visible v0.1.0 and v0.2.0 local specifications, the visible upstream v0.3.0-draft spec/CLI, and this independent v0.3.1 candidate. It does not claim that the upstream ZIP test suite was re-executed.

| Area | v0.1.0 | v0.2.0 | v0.3.0 | v0.3.1 candidate refinement |
|---|---|---|---|---|
| Primary role | Startup + personalization | Provider-neutral control plane | Structured request intake + modular control kernel | Preserves all three layers and makes their boundaries testable |
| Persona MD states | `ABSENT / PRESENT / EMPTY / ERROR` | Retained | Retained | Preserved; dangling symlinks now return `ERROR` |
| Dials | Base 8, advanced 5; group suggestion at 10 | Optional overlay | Optional overlay | Retained; one-time interactive screen restored; advanced set is opt-in; invalid settings never silently reset |
| Request contract | Basic startup inputs | Task Envelope | Raw request + normalized goal + atomic requirements + assumptions + questions + acceptance criteria | Strengthened checks for IDs, list duplicates, typed known constraints, and state consistency |
| Routing | Not the focus | Deterministic capability plan | Intake → Task Envelope → capability planner | Adds backtracking, explicit deny-all empty allow-list, approval precedence, and bounded search budget |
| Registries | Mold IDs | MOLD vs PROC separation | Processor registry | Strict schema/metadata checks for both Mold and Processor registries |
| Result semantics | Output validation concept | Plan result | Result contract described | Adds Result Envelope consistency validator; semantic truth remains `NOT_ASSESSED` |
| Trace | Runtime record concept | Route / version tracking | Trace contract described | Adds in-memory privacy-minimizing trace; raw text omitted by default, hash opt-in, no persistence/network |
| Failure behavior | State branching | Type/policy route diagnostics | Unresolved questions and partial plans | Adds typed errors, no-silent-operation precedence, no-silent-settings-replacement, explicit limits |
| Execution | No LLM/API execution | Plan only | Plan only | Still plan-only; no adapter or external execution falsely claimed |
| Verification | Basic demo/test intent | Determinism checks | Test suite referenced | 92 local regression tests + CLI smoke checks for this independent candidate |

## Retained invariants

1. Top Mold is a control plane, not a monolithic domain expert.
2. Persona and Dials express preferences and do not add capabilities or override hard policy.
3. A plan is not an execution result.
4. `READY` is required before an Intake Packet becomes a Task Envelope.
5. A malformed existing file is an error, not a blank default to overwrite silently.
6. Unknown mandatory constraints remain unverified and cannot produce `COMPLETE`.
7. Provider/domain/device-specific code belongs behind separately declared interfaces.

## New candidate-level hardening

- `requires_approval=false` cannot cancel a prior explicit approval requirement.
- Empty `allowed_execution_modes` is consistently interpreted as deny-all in policy and constraint forms.
- Route search has a configurable positive node budget and 256-step depth bound; exhausting the node budget produces a partial plan and diagnostic.
- A valid Result Envelope requires mutually consistent execution, output, and verification claims.
- Trace generation does not include raw request text by default; an optional SHA-256 digest is explicitly flagged as potentially linkable.
- A settings symlink is not atomically replaced; callers must name the target path explicitly.
- Interactive first-run onboarding is one-time; non-interactive processes neither wait for input nor save default settings as a side effect.

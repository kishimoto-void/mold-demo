# Changelog

## 0.3.1-draft — audit hardening candidate

- Uses a single mutually exclusive CLI operation group to prevent silent flag precedence.
- Keeps task and intake routing independent of optional Persona/Dial configuration files.
- Enforces explicit schema versions on Task Envelopes and Processor Registries.
- Adds deterministic route backtracking and chooses a longest reachable prefix when no full path exists.
- Makes an explicitly empty `allowed_execution_modes` deny all modes rather than being treated as no restriction.
- Surfaces unrecognized soft constraints as warnings; unrecognized mandatory constraints prevent `COMPLETE`.
- Tightens malformed-type handling so contract violations are raised as domain errors rather than incidental `TypeError`s.
- Records `risk_level` in plan output and documents that it is metadata unless an explicit approval policy applies.
- Writes dial settings through a temporary file and atomic replacement after validation.
- Adds a separate Result Envelope validator; status success requires declared outputs and all-PASS verification metadata, while semantic truth remains unassessed.
- Adds an in-memory privacy-minimizing Trace Record builder for plan-only results; raw input is omitted by default and request fingerprinting is opt-in.
- Adds a configurable route-search node budget and explicit `PLANNING_SEARCH_LIMIT` diagnostics; limits recursive route depth to 256 steps.
- Prevents `requires_approval=false` task constraints from weakening an explicit approval requirement.
- Validates Mold Registry schema version and required metadata; unknown constraints are reported as unverified rather than proven violations.
- Restores the one-time interactive first-run dial screen while keeping non-interactive runs non-blocking and side-effect-free.
- Treats dangling Persona symlinks as `ERROR` rather than creating a profile on an unresolved link target.
- Tightens intake uniqueness/context/constraint checks, dial catalog schemas, settings key types, and save error reporting.
- Makes the absent-persona demo isolated in a temporary directory so it is repeatable and does not touch repository runtime files.
- Refuses to replace settings symlinks and treats dangling settings links as errors rather than missing preferences.
- Adds 92 standard-library regression tests and an upstream static audit report.
- Keeps external execution, adapters and semantic output verification explicitly unimplemented.

## 0.3.0-draft — Request Intake and Modular Control Kernel

See the upstream README and changelog. This candidate is based on its visible contracts and CLI; it is not a direct patch of the archived ZIP.

# Top Mold — Universal Control Skeleton Specification

- **Version:** `0.3.1-draft`
- **Compatibility target:** provider / domain / device neutral
- **Reference runtime:** Python 3.10+, standard library only
- **Implementation scope:** request contract validation, declared policy checks, registry validation, deterministic route planning, optional personalization overlay
- **Execution:** not implemented; `execution_status` must remain `NOT_INVOKED`

## 1. Purpose and non-goal

Top Mold is a control plane, not a giant reasoning circuit. It preserves the user's goal, decomposes the request into an explicit contract, checks whether the declared inputs, capabilities and output types can be connected, and makes unknowns or gaps visible.

The generic core must not contain domain-specific expert reasoning, model-specific API calls, UI code, credentials, or assumptions about hidden model internals. These belong in independently versioned processors, specialized molds, adapters, and policy implementations.

## 2. Responsibility map

| Responsibility | Contract / component | Status in candidate |
|---|---|---|
| Interpret raw natural language | Intent Compiler (LLM, human, local parser, or other mold) | Interface described; not implemented |
| Validate structured user intent | Request Intake Packet validator | Implemented |
| Enforce decision consistency | `READY` / `CLARIFICATION_REQUIRED` / `BLOCKED` checks | Implemented |
| Build execution-neutral task contract | Task Envelope conversion | Implemented for `READY` packet |
| Declare capabilities | Processor Registry | Implemented as JSON contract |
| Plan type-compatible steps | Capability Planner | Implemented; plan only |
| Apply hard execution permission | Explicit policy fields in planner | Minimal declarative gate implemented; not a security sandbox |
| Customize presentation | Persona / Dial overlay | Implemented as data generation only |
| Save settings safely | Validated atomic settings write | Implemented locally |
| Execute LLMs/tools/APIs | Adapter / executor | Not implemented |
| Validate Result Envelope field/status consistency | `core/result_contract.py` | Implemented; semantic truth is not assessed |
| Build a privacy-minimizing trace record | `core/trace.py` | In-memory record builder implemented; no persistence/network |
| Verify semantic truth of model output | Result verifier / source checker | Not implemented |
| Persist full runtime trace | Trace store | Not implemented; no trace database |

## 3. Request Intake Packet

Required fields:

- `schema_version`: currently `1.0`.
- `raw_request`: original text; never overwritten by its normalization.
- `normalized_goal`: explicit target statement.
- `atomic_requirements`: unique `id`, `text`, `priority` (`must / should / could`), and `source` (`explicit / inferred`).
- `known_constraints`: unique `id`, `kind`, `value`, and optional `severity`.
- `assumptions`: unique `id`, `statement`, `confidence` in `[0,1]`, `impact` (`low / medium / high`), and source.
- `open_questions`: unique `id`, `question`, and boolean `blocking`.
- `acceptance_criteria`: unique `id` and `text`.
- `routing`: `input_types`, ordered `required_capabilities`, `output_contract.required_types`, `risk_level`, and optional explicit `policy`.
- `decision.status`: `READY`, `CLARIFICATION_REQUIRED`, or `BLOCKED`.

Decision invariants:

1. `READY` cannot coexist with a blocking open question.
2. `CLARIFICATION_REQUIRED` requires at least one blocking question.
3. `BLOCKED` requires a reason.
4. Only `READY` can be converted into a Task Envelope.
5. A validator confirms structure and internal consistency; it does not prove that the natural-language interpretation is correct.

## 4. Task Envelope

The route planner requires `schema_version`, `task_id`, `goal`, `input_types`, ordered `required_capabilities`, `output_contract.required_types`, `constraints`, and optional `policy`, `risk_level`, and context fields.

The `constraints` list supports these kinds directly:

- `forbidden_execution_mode`: exclude a named execution mode.
- `allowed_execution_modes`: restrict routing to the listed modes; an explicit empty list permits none.
- `requires_approval`: boolean. If true and `policy.approval_granted` is not true, planning is blocked.

These execution-policy kinds are enforced conservatively: a `severity` annotation cannot downgrade an explicit prohibition, an allowed-mode restriction, or a required approval into a soft preference. A later `requires_approval=false` cannot cancel an earlier `true` requirement. An explicit empty allowed-mode list denies all execution modes.

An unknown `must` constraint without a registered evaluator prevents `COMPLETE`; the planner reports it as unverified rather than as a proven violation. Unknown `should / could` constraints remain visible as warnings and do not get silently marked as satisfied. The planner cannot prove constraints that require domain-specific or semantic evaluation. Accordingly, `constraint_violations` is reserved for confirmed violations; unassessed items belong in `unverified_constraints`.

`risk_level` is recorded metadata; it does not by itself grant or deny execution. Any approval policy must be explicit. A future risk policy must specify its decision table and tests before claiming enforcement.

## 5. Processor Registry

Each Processor Descriptor declares:

- `id`, `version`, `status` (`active / disabled / deprecated / experimental`)
- `capabilities`: unique list of capability labels
- `accepts`: accepted input types; empty means no declared input-type restriction
- `produces`: output types emitted by the declared capability
- `execution_mode`: provider-neutral mode label
- `priority`: integer used as a stable tie-breaker
- optional `adapter_id` and `entrypoint` metadata

Only processors with `status=active` can be selected. A Processor is a declared candidate, not proof that its adapter exists or can execute. Duplicate IDs and malformed descriptors are errors.

## 6. Deterministic route planning

1. Validate the Task Envelope and Processor Registry.
2. Apply explicit forbidden and allowed execution-mode constraints.
3. If approval is required but not recorded, return `BLOCKED` with no route steps.
4. Search capabilities in the order requested by the Task Envelope.
5. For each step, the candidate must declare the capability and accept at least one currently available input type, unless `accepts` is empty.
6. After a step, only that processor's declared `produces` types become the current types for the next step.
7. Candidate ordering is priority descending, then Processor ID ascending.
8. Prefer a full compatible chain. If no full chain exists, return the longest reachable prefix with a diagnostic at the first unsatisfied capability.
9. Check final output types against `output_contract.required_types`.
10. A plan is `COMPLETE` only when all requested capabilities and output types are covered and there is no unverified mandatory constraint.

The result includes `plan_mode=PLAN_ONLY`, `execution_status=NOT_INVOKED`, and `execution_invoked=false`. These fields must not be changed to success by a planning-only component.

## 7. Result Envelope

A planning result contains:

- `schema_version`, `task_id`, `risk_level`
- `plan_status`: `COMPLETE / PARTIAL / BLOCKED`
- `plan_mode`: `PLAN_ONLY`
- `execution_status`: `NOT_INVOKED`
- `execution_invoked`: `false`
- `steps`, `capability_coverage`, `unmet_capabilities`, `unmet_output_types`
- `constraint_violations` / `unverified_constraints`
- `diagnostics`, `warnings`, `final_types`

`core/result_contract.py` validates a separate processor Result Envelope for consistent status claims. `--result` can load and validate this contract, optionally checking `--expected-task-id`. Validation sets `claims_validated=true` while keeping `semantic_correctness=NOT_ASSESSED`; it is not semantic fact-checking and it does not execute a processor. A future executor must still populate actual invocation status, timestamps, errors, provenance/evidence, and verification checks. It must not overwrite the plan result or claim semantic success simply because an API returned HTTP 200.

`core/trace.py` can build an in-memory trace from a task and plan using `--trace TASK_JSON PLAN_JSON`. Raw request text is omitted. A SHA-256 fingerprint is only included with explicit `--fingerprint-request`; hashes may still be linkable. The trace is emitted to stdout and is neither persisted nor transmitted by this prototype. Trace generation accepts only plan-only records (`plan_mode=PLAN_ONLY`, `execution_status=NOT_INVOKED`, `execution_invoked=false`); it rejects a record that claims execution occurred.

## 8. Persona, Dials and Session Overrides

- **Persona Seed / Capsule:** presentation and work-style preferences.
- **Dials:** adjustable output preferences, 1–5.
- **Session Override:** instruction limited to the current task.
- **Hard Policy:** security, permission, consent and mandatory constraints.

Precedence for presentation settings is `hard_policy > task_contract > session_override > dial_overlay > persona_seed`. That ordering is not permission to reinterpret a task contract or weaken safety rules. Persona and dials do not create new abilities or change the processor registry.

The basic dial set is `D-001`–`D-008`; advanced dials `D-009`–`D-013` are opt-in. When 10 or more independent dials are enabled, suggest grouping or deduplication only. Never merge, delete or change settings silently. A selected advanced dial may be activated explicitly by the user.

## 9. Startup and persistence

Persona file states:

- `ABSENT`: no file exists; standard settings remain possible.
- `PRESENT`: readable, non-empty file; preserve it.
- `EMPTY`: file exists but contains only whitespace; ask before replacing.
- `ERROR`: unreadable path, invalid UTF-8, or non-file path; never treat as absence.

Personalization settings are validated before saving. Persist through a same-directory temporary file and atomic replacement. Corrupt existing settings must be reported without being overwritten. On the first interactive terminal launch, the wizard offers Persona setup and displays the eight base dials once; it saves defaults after the user continues through setup. Later ordinary launches do not repeat the dial screen; `--configure` explicitly reopens it. Non-interactive launches do not wait for input and do not persist defaults as a side effect. Task/intake planning must not depend on valid Persona or Dial files.

## 10. Extension and failure rules

- Keep `MOLD-XXX` as responsibility/contract units and `PROC-XXX` as declared capability providers.
- A new provider must declare version, capabilities, accepted/produced types, execution mode, status and failure behavior.
- Unknown required capability → `NO_PROVIDER`.
- Declared but incompatible input → `INPUT_TYPE_MISMATCH`.
- Execution policy excludes all candidates → `FORBIDDEN_EXECUTION_MODE`.
- Missing approval → `APPROVAL_REQUIRED` and `BLOCKED`.
- Required final output not declared → `OUTPUT_CONTRACT_UNMET` and `PARTIAL`.
- Unrecognized mandatory constraint → `HARD_CONSTRAINT_UNVERIFIED` and `PARTIAL`.
- Invalid input structure must become a typed user-facing error, not an uncaught traceback.

## 11. Explicit non-goals for this version

No natural-language inference, LLM/API execution, adapter authentication, tool side effects, automatic retries, persistent trace database, semantic result verification, cross-provider behavioral equivalence, smartphone/PC GUI automation, or production security boundary. These are separate modules requiring separate acceptance tests.

## 12. Acceptance criteria

- Identical input and identical registry produce identical route plans.
- Invalid or contradictory Intake Packets do not produce a Task Envelope.
- Persona absence does not block routing; corrupt personalization files do not block `--task` or `--intake` routing.
- Existing settings remain unchanged after failed validation.
- A forbidden or disallowed mode is never selected.
- Empty allow-list means no mode is allowed.
- Unknown mandatory constraints do not yield `COMPLETE`.
- Only `READY` intake proceeds to planning.
- CLI refuses multiple conflicting operations instead of silently choosing one.
- Every route explicitly reports `NOT_INVOKED`.
- Malformed Result Envelopes are rejected, and a successful status requires declared outputs plus all-PASS verification checks.
- Trace output excludes raw request text by default and rejects mismatched task IDs or inconsistent execution fields.
- Route search has a positive integer node limit and reports a partial plan if it is reached; oversized route depth is rejected before recursion.
- Unit tests pass under Python 3.10+ using only the standard library.

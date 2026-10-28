# Generic Middle Mold v0.1.0

## Goal

A reusable, personality-neutral process planner. The programming/debugging workflow is a demo
profile, not the only task this mold can handle.

## Contract boundary

Provisional neutral input:
- `goal: str`
- `constraints: sequence[str]`
- `context: mapping`
- `task_domain: str`
- `requested_outputs: sequence[str]`

Current output:
- `process_plan`
- `knowns`
- `hypotheses`
- `unknowns`
- evaluation checks, stop conditions, assumptions, and limitations

`requested_outputs` is currently captured and validated but not used to filter output fields. This is a known prototype limitation.

## Existing project compatibility

- Does not overwrite the existing `middleｰmold/middle_mold.py`, which is the learning-process reference implementation.
- Uses Joint Program contract version `1.1.0` from the prototype created alongside this package. Confirm the target repo's canonical contract version before integration.
- Does not call an LLM or execute code.
- Keeps goal/constraints/context separate from persona preferences and execution behaviour.
- Does not silently reorder, fill in missing requirements, or promote hypotheses into facts.

## Confirmed vs provisional

### Design constraints preserved from project context
- Middle is the process-configuration layer between Top and Bottom.
- It should be reusable and not embed persona identity or LLM-specific behaviour.
- Facts, hypotheses, and unknowns should remain distinguishable.
- Plans and actual execution results must not be conflated.

### Provisional hypotheses
- `goal`, `constraints`, and `context` are a sufficient minimal generic input contract for the first prototype.
- Debugging is selected only by explicit `task_domain="programming_debugging"`.
- The context keys `observations`, `hypotheses`, and `unknowns` are accepted as sequences of strings.
- The field names are candidate interface names, not yet accepted as the final Top/Middle/Bottom contract.
- No data-type or semantic compatibility proof is claimed.

## Run

```bash
python -m middle.middle_mold_core
python -m pytest -q
```

Python 3.10+ is recommended. Runtime uses only the standard library; pytest is needed for tests.

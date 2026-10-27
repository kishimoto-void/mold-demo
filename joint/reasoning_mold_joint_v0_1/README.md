# Reasoning Mold — Joint Program prototype v0.1.0

## Purpose

This prototype implements the Joint Program's **assembly and validation boundary** for the
explicit `Top → Middle → Bottom` (TMB) pipeline. It does not call an LLM and does not execute
the molds. It also supports `TM` and `MB` pairwise validation.

## Contract rules implemented

- Stage order is explicit; no automatic reordering.
- TMB validates Top→Middle and Middle→Bottom independently.
- TMB also checks the Top's required external inputs and Bottom's exposed outputs.
- Required downstream input fields must be present in the immediately upstream mold's outputs.
- Disabled molds, duplicate mold IDs, and unsupported joint contract versions are reported.
- Invalid configurations are not auto-repaired. `export()` refuses to export invalid assemblies.
- The legacy resource-to-process adapter remains available as `LegacyResourceJoint` when
  `resources.py` can be imported or a registry is explicitly supplied.

## Important distinction: confirmed vs. provisional

### Preserved from existing project context
- Joint Program is an outer integration layer, not a universal internal mold standard.
- TM, MB, and TMB are supported modes.
- TMB checks both pair boundaries and whole-configuration consistency.
- The Joint layer arranges the requested components, checks required parts, I/O, connection
  conditions, and versions; it does not perform LLM reasoning or auto-optimize order.
- The existing `ResourceSpec` / `ProcessSpec` style API is retained through `LegacyResourceJoint`.

### Provisional hypotheses used by this implementation
- Field names are the initial compatibility unit. Field-level data types, transforms, and
  semantic equivalence are not yet specified, so this prototype does not claim to validate them.
- A required input is satisfied only by the immediately preceding mold's declared outputs.
- `external_inputs` defaults to `("user_input",)`.
- The example field names in `demo_contracts()` are illustrative only. They are not a normative
  Top/Middle/Bottom schema and should be replaced after the three molds publish their contracts.
- The assembly schema version `0.1.0` is a prototype version, not a project-wide release.

## Run

Requires Python 3.10+ and pytest for the test suite.

```bash
python -m joint.joint_program
python -m pytest -q
```

No third-party runtime dependency is needed by `joint_program.py`; pytest is only needed to run tests.

## Suggested next step

Define and review actual `MoldContract` instances from the current Top, Middle, and Bottom
specifications, especially the input/output field names and types. Keep uncertain mappings
explicitly provisional until accepted.

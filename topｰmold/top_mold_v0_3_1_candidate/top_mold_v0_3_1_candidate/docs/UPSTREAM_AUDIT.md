# Upstream v0.3.0 Static Audit

**Audited public references:**

- [v0.3.0 README](https://github.com/kishimoto-void/mold-demo/blob/main/top%EF%BD%B0mold/DEMO/README.md)
- [v0.3.0 specification](https://github.com/kishimoto-void/mold-demo/blob/main/top%EF%BD%B0mold/DEMO/TOP_MOLD_SKELETON.md)
- [v0.3.0 main.py](https://github.com/kishimoto-void/mold-demo/blob/main/top%EF%BD%B0mold/DEMO/main.py)
- [v0.3.0 changelog](https://github.com/kishimoto-void/mold-demo/blob/main/top%EF%BD%B0mold/DEMO/CHANGELOG.md)

The upstream `main` tree has a `topｰmold/DEMO` directory containing the README, specification, changelog, `main.py`, mold contract, and `top_mold_skeleton_v0.3.0.zip`. The imported `core/`, `config/`, and `tests/` files are not exposed as unpacked files in that directory listing. The README describes those paths as part of the bundle, so a user needs to unpack the ZIP to obtain the full runnable project. In this environment the binary ZIP could not be executed directly; this report therefore labels findings from the accessible code as **static findings**, not as a rerun of the archived test suite.

## Findings

| ID | Severity | Finding | Effect | Refinement |
|---|---|---|---|---|
| UP-01 | Medium | `main.py` accepts several operation flags at once. It has explicit conflict checks for `--configure`, but not a common mutually exclusive group for `--demo`, `--task`, `--intake`, and `--show-overlay`. | Depending on branch order, a command such as `--demo ... --task ...` can silently run only one operation. | Candidate CLI uses an argparse mutually exclusive group. Regression test confirms conflicting operations are rejected. |
| UP-02 | Medium | The README's quick-start assumes `core/`, `config/`, and `tests/` exist next to `main.py`, while the tracked folder listing exposes those files only inside the bundled ZIP. | Running `python main.py` from the unextracted folder may fail imports or config reads. | Candidate pack is self-contained and documents `cd` into the unpacked directory before running commands. Upstream should either extract/commit the files or include explicit unzip steps. |
| UP-03 | Low | The v0.3.0 README documents several components and states that tests were added, but the repository's visible DEMO subtree does not expose the test files for direct source review. | Reviewers cannot audit exact coverage without extracting the ZIP. | Candidate includes the regression test source alongside the implementation and a validation report. |
| UP-04 | Medium | The accessible v0.3.0 CLI code branches into `--show-overlay`, `--demo`, `--intake`, and `--task` in precedence order rather than rejecting simultaneous operations. | A second requested operation may be silently ignored. | Same correction as UP-01; tested. |

## Scope boundaries retained

The upstream spec correctly distinguishes planning from execution, treats Persona/Dials as optional overlays, and says the adapter and semantic result reconciliation are not implemented. The candidate preserves those boundaries instead of relabelling them as completed features.

## Important limitation

This is not a claim that the upstream ZIP has failing tests. Its full archive was not executable through the available repository-fetch mechanism, so no statement is made about the upstream suite's pass/fail count. The 92-test result in `VALIDATION_REPORT.md` is for the independent v0.3.1 candidate package supplied alongside this report.

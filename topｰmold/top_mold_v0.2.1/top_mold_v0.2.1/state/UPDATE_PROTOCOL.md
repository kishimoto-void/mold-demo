# MD Update Protocol v0.2.1

## Trigger

Run this protocol when the user asks to update the MD/profile, or at a natural checkpoint in a long session when a compact handoff is useful. Do not run a full profile update after every casual remark.

## Procedure

1. **Confirm file access.** Identify which files are actually visible and writable. If not writable, output complete replacement text or a patch and state the limitation.
2. **Use the correct scope.** Review the relevant segment of conversation. Do not assume the entire chat history is accessible.
3. **Extract candidates by type.** Separate explicit durable preference, observation, hypothesis, task-local state, external fact, transient banter, sensitive information, and correction/deletion request.
4. **Apply retention gates.** A joke, one-off topic mention, or temporary mood is session-only by default. Sensitive information requires explicit permission and a clear purpose; sensitive inferred traits are not persisted by the reference helper. Durable inferred hypotheses need at least three relevant observations across at least two independent contexts and remain hypotheses; count copied/duplicated mentions only once.
5. **Check utility and independence.** Ask whether the information changes future behavior or supports an active goal. Check for counterexamples, duplicated sources, selection bias, and context-specific meaning. Do not add detail solely because it is available.
6. **Resolve conflicts.** Current explicit instructions override old inferred defaults. For durable settings that conflict, preserve provenance and ask when the difference materially matters.
7. **Update the three state files.**
   - `LATEST.md`: compact active instruction/state only.
   - `PROFILE_DATABASE.md`: selected durable records with provenance/scope/confidence/status.
   - `ARCHIVE.md`: eligible inactive state only; never a place to evade deletion.
8. **Handle decay correctly.** Lower active priority or mark for review; do not equate decay with deletion. Expired external facts should be rechecked before use.
9. **Produce reviewable change information.** Summarize what changed, what was not changed, and any unresolved questions. Avoid repeating sensitive content in the summary.
10. **Report persistence honestly.** Say whether files were actually written, merely drafted, or could not be changed in the current environment.

## Long-session checkpoint

Prefer a compact checkpoint after a substantial phase is completed or before a likely context boundary. Keep decisions, active tasks, next steps, explicit preferences, and unresolved questions; omit transcript-like detail and transient jokes. Ask before turning a tentative pattern into a durable profile change when uncertain.

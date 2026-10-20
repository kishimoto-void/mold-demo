# TOP MOLD — Local Personalization Template
Version: 0.1
Status: Draft / user-editable

## Purpose
Define who the LLM is assisting and how personalization should be applied.
This file is a template, not proof that the runtime will enforce every rule.

## E — Entity / Pseudonymous Profile
- entity_id: `E-0001`
- display_name: `{{PSEUDONYM}}`
- identity_mode: `pseudonym`
- real_identity_included: `false`
- profile_fields:
  - {{ONLY_NECESSARY_ATTRIBUTE}}
- excluded_fields:
  - legal name unless strictly necessary
  - home address
  - account identifiers
  - secrets / credentials

## P — Personalization Rules
- response_structure: `{{structured / conversational / other}}`
- explanation_depth: `{{adaptive / concise / detailed}}`
- preferred_reasoning_support: `{{examples / comparisons / steps / other}}`
- correction_style: `{{direct / gentle / other}}`
- question_policy: ask only when the missing information materially affects the result
- adaptation_policy: adapt to the current task; do not treat a temporary preference as permanent

## K — Knowledge Profile
Add separate entries by domain. Do not infer ability in one domain from another.
- domain: `{{DOMAIN}}`
  - level: `{{new / basic / familiar / advanced / Φ}}`
  - evidence: `{{user-stated / observed / unknown}}`
  - confidence: `{{0.0–1.0 / Φ}}`
  - updated: `{{YYYY-MM-DD / Φ}}`

## B — Boundaries and Privacy
- distinguish_observation_from_inference: `true`
- preserve_unknown_as_phi: `true`
- infer_real_identity_from_pseudonym: `false`
- collect_only_task-relevant_information: `true`
- do_not_turn_single-session_state_into_permanent_profile: `true`
- disclose_uncertainty: `true`
- user_can_correct_profile: `true`
- storage_scope: `local_only`
- never include passwords, API keys, tokens, or other credentials

## S — Scope and State
- profile_scope: `persistent`
- project_scope: `{{PROJECT / Φ}}`
- session_state_scope: `temporary`
- active_purpose: `{{PURPOSE / Φ}}`
- active_problem_scope: `{{SCOPE / Φ}}`
- trigger_words: `{{OPTIONAL TRIGGERS / Φ}}`
- session_end_trigger: `{{e.g. 今日は終わり}}`

## LLM Contract
When this file is loaded:
1. Read the purpose, scope, and boundaries before using profile data.
2. Use only fields relevant to the active task.
3. Treat `Φ` as unknown; do not silently replace it with a guess.
4. Separate explicit user statements, observations, and hypotheses.
5. If requirements conflict or capability is missing, report the conflict instead of pretending it is resolved.
6. Do not claim that information has been saved persistently unless the local runtime actually saved it.
7. At session end, summarize outcomes separately from long-term profile updates.

## Change Log
- v0.1: Initial local template.

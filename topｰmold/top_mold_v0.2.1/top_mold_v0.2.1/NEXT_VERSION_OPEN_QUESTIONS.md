# Open Questions Carried Forward — Top Mold v0.2.1

These questions are intentionally left open in v0.2. They should be resolved through implementation experiments, actual use, and conformance testing rather than speculative default choices. The presence of a question here is not a promise that it will be solved automatically in the next release.

## 1. Dial calibration

- What default ranges make personalization useful without causing overfitting or unnecessary verbosity?
- Are the current global fallback and enabled-domain override rules understandable and useful for beginners across providers, or should some domains use named levels with domain-specific meanings?
- How should `initiative` map to different model/provider capabilities when the same numeric value does not produce the same behavior?
- Should users be able to set a per-domain maximum on proactiveness in addition to the current exact override rule?

## 2. Memory and forgetting

- What retention/decay periods are useful for each record type and domain? The current half-lives are illustrative, not empirically validated.
- Is the conservative threshold of three relevant observations across at least two independent contexts useful in practice, and what confirmation threshold should distinguish a hypothesis candidate from an active profile record?
- Which durable preference changes should be applied immediately, proposed for confirmation, or stored as a candidate?
- How should a user correction supersede conflicting sources while preserving only the history that remains permitted?
- How can a deletion request be verified across copies the current LLM cannot access? The contract must not imply that inaccessible provider stores were deleted.

## 3. State consistency and portability

- Should the three Markdown state files later be supplemented with a small manifest, record IDs, revision numbers, and hashes to detect stale copies or concurrent updates?
- How should conflicting edits from two different LLMs be merged without silently overwriting explicit user settings?
- What is the best checkpoint trigger for long conversations: user request only, token/context warning when available, completed task phase, or a combination?
- Which state fields should be mandatory versus optional for beginner use?

## 4. Cross-domain personal hub

- How should a source adapter declare what data it can read, update, monitor, or delete, and with what permissions?
- What consent model is appropriate when an observation from one domain could improve a suggestion in another domain, beyond the current relevance, scope, sensitivity, and permission checks?
- How should current facts (prices, release dates, events, ticket lotteries, stock) be refreshed and invalidated by source-specific rules?
- How can recommendations be evaluated against useful outcomes rather than only subjective plausibility?

## 5. Cross-provider conformance

- Which practical test set can measure whether different LLMs follow the same dial intent?
- How should a provider-specific adaptation be represented without polluting the portable core contract?
- What fallback behavior is appropriate when the model cannot write files, cannot browse, or cannot schedule notifications?
- Which tests require human judgment and cannot be reliably automated in this reference package?

## 6. Scope for v0.3 planning

A future version should prioritize the open questions with evidence from a small real-world trial. Until then, the v0.2 schema family MUST NOT present these dimensions as empirically solved, and MUST preserve the current conservative defaults and user's ability to override them.

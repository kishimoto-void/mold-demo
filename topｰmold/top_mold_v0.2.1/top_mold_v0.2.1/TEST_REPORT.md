# Test Report — Top Mold v0.2.1

**Result: PASS** for the bundled reference package checks executed in the build environment.

- Runtime: Python 3.13.5
- Third-party Python dependencies: none required
- Automated unit / contract / conformance tests: **97 passed, 0 failed**
- Python byte-compilation: passed
- JSON parse checks: passed for configuration, profile-record schema, both example profiles, and golden conformance cases
- CLI smoke checks: passed for normal text output, JSON output, explicit mode lock, and multiple output-format reporting
- ZIP integrity / extraction checks: passed on the final packaged archive

## Test areas

1. Five task modes, topic-only false positives, common quoted-action and local-negation cases.
2. Compound requests, explicit mode lock/unlock, precedence, and output-format independence.
3. Negative output-format requests, format mentions used only as discussion topics, and preservation of multiple explicit output formats.
4. Configuration version/range/type validation, domain-profile shape, required dial semantics, kernel, and security invariants.
5. Transient content and sensitive-data retention gates, including explicit permission plus clear-purpose requirements.
6. Hypothesis evidence threshold, independent-context gate, sensitivity guard, and invalid policy inputs.
7. External fact source/validity requirements.
8. Decay calculations, stable durable preferences, and rejection of boolean, negative, NaN, infinity, and malformed numeric inputs.
9. Deletion precedence and distinction between archive, decay, and deletion.
10. Latest state / profile database / archive separation and update-protocol requirements.
11. Cross-domain execution-kernel documentation, domain override rules, dial semantics, and control/data separation.
12. Explicitly deferred calibration, provider limits, user agency, privacy, human dignity, and truthful reporting.

## Reproduction

From the extracted package root:

```bash
python -m unittest discover -s tests -v
python -m compileall -q top_mold tests
python -m json.tool config/top_mold.json
python -m json.tool schemas/profile_record.schema.json
python -m json.tool examples/personal_hub_profile.json
python -m json.tool examples/study_teacher_profile.json
python -m json.tool tests/conformance_cases.json
python -m top_mold.engine "トップモールドを作成して、厳密にテストして"
python -m top_mold.engine --json "ChatGPT的にどう思う？ これをZIPにして"
python -m top_mold.engine --lock design "テストして"
python -m top_mold.engine --json "Markdown形式で説明して、最後にJSONで出力して"
unzip -t ../top_mold_v0.2.1.zip
```

## Important limits

These checks validate the package files and deterministic reference helpers only. They do not prove that any external LLM follows the behavior contract. The package does not itself connect accounts, read purchase histories or calendars, run background monitoring, send notifications, or persist files across providers. Those require separate integrations and permissions. Cross-provider behavior, dial calibration, usefulness of personalization, and optimal forgetting schedules remain unverified. Rule-based text classification is still heuristic and may miss paraphrases, nested quotations, irony, or complex scope/negation. See `NEXT_VERSION_OPEN_QUESTIONS.md` for intentionally deferred questions.

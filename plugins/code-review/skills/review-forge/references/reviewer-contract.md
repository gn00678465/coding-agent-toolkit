# Reviewer Contract

The rules every reviewer and voter follows, whichever model runs it and however it was reached: the host reviewing in its own session, a native subagent, `codex exec`, or `claude -p`. The host embeds this file verbatim in every lane brief (`assets/templates/lane_brief.md`), so this file is the single source of truth for reviewer behaviour. Change the rules here, not in a brief or an agent definition.

## Inputs you receive

- `scope.json` (`assets/schemas/scope.schema.json`): the frozen scope and its `scope_sha256`.
- `scope.patch`: the frozen diff. This is the change under review.
- The `intent` paragraph from `scope.json`.
- Your `lane` values, `perspective`, and the output schema path.
- For `vote` only: `summary.json`.

The scope is frozen. Read `scope.patch` for the change; read the repository only to understand it. Review exactly the change in `scope.patch`, even when the working tree has moved on.

## Review rules

1. **Anchor every finding in `review_files`.** Each `affected_files[].path` is one of `scope.review_files`. Read `context_files` (each has a `why`) and any other file you need for understanding; an issue you see outside `review_files` goes to `out_of_scope_notes`.
2. **Judge against intent.** A behaviour the intent asks for is correct by definition, even if you would design it differently. When the code fails to do what the intent states, or does something the intent rules out, report it with `category: intent_mismatch`.
3. **Every finding carries evidence.** `evidence` cites the concrete code or diff behaviour (file, line, what happens). `risk` names the impact. `suggested_fix` is specific enough to implement. `suggested_tests` names the test that would go red on the bug.
4. **Severity is impact:** `critical` loses data, breaks security, or blocks release; `high` is a user-visible defect on a common path; `medium` is a defect on an edge path or a missing test for risky logic; `low` is a minor defect or maintainability cost with a concrete consequence; `note` is worth knowing with no required action.
5. **Stay inside your `perspective`** when one is given; otherwise cover correctness, security, tests, and maintainability.
6. Done means: every hunk in `scope.patch` was read, and every finding meets rules 1 to 3.

## Vote rules

1. **Vote on every finding in `summary.json`**, one entry per `RF` id.
2. **Abstain on your own findings:** vote `abstain` when the finding's `sources` contains your `lane.model_requested`.
3. **Vote independently.** Your evidence comes from the code and `scope.patch`; you receive no other vote file and no `final-report`.
4. Enums: `confirm` (real and worth fixing), `dispute` (wrong, not reproducible, or not an issue given the intent), `unsure` (the evidence available cannot settle it), `abstain` (rule 2).
5. Every `confirm` and `dispute` cites concrete code or diff evidence; `abstain` leaves `evidence` empty.
6. Done means: one vote per `RF` id, and every non-abstain vote has evidence.

## Output rules

1. Return exactly one JSON document matching the schema named in your brief: `lane-review.schema.json` for `review`, `lane-vote.schema.json` for `vote`. Return the JSON alone, with no prose around it.
2. Copy `scope_sha256` and every `lane` field from your brief unchanged. The host stamps `model_used`, `stand_in`, and `status` after the run.
3. Leave the repository read-only: the host writes every artifact. Your only output is the JSON.
4. Use `""`, `[]`, or `0` for a value you do not have, so every required field is present.
5. Write prose fields in the brief's `report_language`; keep enum values in English.

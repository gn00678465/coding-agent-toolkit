# Review Forge Lane Brief

- `command`: <!-- review | vote -->
- `feature_dir`: <!-- .review/<feature>/ -->
- `scope_file`: <!-- .review/<feature>/scope.json -->
- `scope_sha256`: <!-- SHA-256 of scope.json bytes -->
- `patch_file`: <!-- .review/<feature>/scope.patch -->
- `summary_file`: <!-- .review/<feature>/summary.json, vote only; omit for review -->
- `output_schema`: <!-- absolute path to lane-review.schema.json or lane-vote.schema.json -->
- `perspective`: <!-- correctness | security | tests | maintainability | ... ; empty for vote -->
- `report_language`: <!-- en | zh-TW | ... -->

## Lane

<!-- Copy into the output unchanged. -->

- `label`: <!-- unique lane label, e.g. codex-gpt-6.1-sol -->
- `kind`: <!-- host-native | codex | claude -->
- `vendor`: <!-- anthropic | openai | ... -->
- `model_requested`: <!-- model slug or alias -->
- `model_used`: <!-- same as model_requested; the host overwrites it -->
- `stand_in`: `false`
- `status`: `complete`

## Intent

<!-- intent.statement from scope.json, verbatim. -->

## Review Files

<!-- scope.review_files, one per line. -->

## Context Files

<!-- scope.context_files as `path`: why. -->

## Reviewer Contract

<!-- references/reviewer-contract.md, verbatim. -->

---
name: review-forge
description: Use when orchestrating a code review across multiple models or agents, including other vendors' models through the Codex or Claude Code CLI; freezing a review scope and intent; synthesizing or cross-voting findings; producing a confidence-ranked final report; or fixing, testing, and verifying approved findings, with every artifact kept under .review/.
---

# Review Forge

Review Forge runs a conservative, feature-scoped code review. Every reviewer, whichever model or vendor, reviews one **frozen scope** against one stated **intent** and returns one **JSON artifact** that matches a schema. The host turns those artifacts into a human-controlled checklist, and fixes only what a human checks.

```text
scope → review → synthesize → vote → report → (human checks items) → fix → verify
```

## Commands

- `scope`: freeze the review scope and intent into `scope.json` and `scope.patch`.
- `review`: produce one review artifact per lane.
- `synthesize`: merge the review artifacts into `summary.json` and `summary.md`.
- `vote`: produce one vote artifact per lane on every `summary.json` finding.
- `report`: aggregate the votes into `final-report.json` and `final-report.md`.
- `fix`: implement checked items only, run tests, update status.
- `verify`: verify fixed items from an independent perspective, update status.

`review` and `vote` run `scope` first when `scope.json` is missing. If the user names no command, infer the safest one from the request; when ambiguous, use `review`. Only `fix` modifies product code.

## Inputs

Resolve or ask for these before doing work:

- `target`: files, a diff, a PR, a branch, a commit range, or the working tree. Resolved by `scope`.
- `base`: comparison ref. Resolved by `scope` when omitted.
- `intent`: the user's own statement of what the change is meant to do. Resolved by `scope` when omitted.
- `feature`: artifact subfolder name. If omitted, infer from the branch name, PR title, changed package, or a short sanitized summary of the diff.
- `feature_dir`: default `.review/<feature>/`.
- `command`: one of the commands above.
- `model`: the model name for a single-lane `review` or `vote`, such as `claude-opus-5-5` or `gpt-6.1-sol`. Defaults to the host's own model.
- `lanes`: models to fan `review` and `vote` out to, as `<kind>:<model>@<effort>`, such as `host:claude-opus-5-5@xhigh, codex:gpt-6.1-sol@xhigh`. See [Lanes](#lanes).
- `perspective`: optional review focus, such as correctness, security, tests, or maintainability.
- `model_weights`: optional vote weights, for example `gpt-6.1-sol: 1.5`. Unlisted models weigh `1.0`.
- `report_language`: default `auto` (follow the user's prompt language); explicit values such as `en`, `zh-TW`, or `ja`.
- `auto_fix_allowed`: default `false` unless the user explicitly asks to fix.
- `test_command`: optional validation override.

## Artifacts

```text
.review/<feature>/
  scope.json            scope.patch
  <model>.json          # one per review lane; <model>-<perspective>.json for extra perspectives
  summary.json          summary.md
  <model>-vote.json     # one per vote lane
  final-report.json     final-report.md
  fix-plan.md           verify.md         status.md
  .lanes/<label>/       # lane briefs and raw CLI output, only when lanes ran
```

**JSON is the record.** Each JSON artifact matches its schema in `assets/schemas/`, and the `.md` files are rendered from the JSON with the templates in `assets/templates/`:

| Artifact | Schema | Written by |
| --- | --- | --- |
| `scope.json` | `scope.schema.json` | host, `scope` |
| `<model>.json` | `lane-review.schema.json` | host, from a lane's output |
| `summary.json` | `summary.schema.json` | host, `synthesize` |
| `<model>-vote.json` | `lane-vote.schema.json` | host, from a lane's output |
| `final-report.json` | `final-report.schema.json` | host, `report` |

Validate every JSON artifact before writing it: `python3 -I <this skill dir>/scripts/validate.py <schema-name> <file>` (exit 0 valid, 1 invalid, 3 jsonschema missing: then check every required field against the schema by hand).

**Checkboxes in `summary.md` and `final-report.md` are the only approval record.** Humans edit them; re-rendering a `.md` carries each `RF` id's checkbox state over unchanged.

Each command writes only its own artifacts:

- `scope`: `scope.json`, `scope.patch`.
- `review`: one `<model>.json` per lane, plus `.lanes/` when lanes ran.
- `synthesize`: `summary.json`, `summary.md`.
- `vote`: one `<model>-vote.json` per lane, plus `.lanes/` when lanes ran.
- `report`: `final-report.json`, `final-report.md`.
- `fix`: `fix-plan.md`, `status.md`, and the product code for checked items.
- `verify`: `verify.md`, `status.md`.

Use stable names without timestamps, unless the user asks to keep several historical runs. `fix-plan.md`, `verify.md`, and `status.md` use their templates in `assets/templates/`.

## Required Initial Inspection

Before producing artifacts or modifying code, inspect:

- repo status and uncommitted changes;
- existing `.review/` feature folders and artifacts;
- `.gitignore` for `.review/`;
- package, build, and test configuration;
- project-specific instructions for tests, lint, typecheck, or CI.

Keep unrelated user changes intact. If `.review/` is not ignored, recommend adding it to `.gitignore`; edit `.gitignore` only when the user asks.

## Scope Command

`scope` decides what every reviewer sees. It runs once per feature; every later command reads its output and none re-infers it.

### 1. Target

Use the first rule that applies, and record it in `resolved_by`:

1. `explicit`: the user named files, a diff, a PR, a branch, a commit range, or a base ref.
2. `recent_work`: the user's message refers to recent work ("the change I just made"). Gather the files that work touched, from the conversation and recent commits, as a `files` target.
3. `uncommitted`: the working tree or index has changes. Target the working tree, staged and unstaged.
4. `branch_diff`: compare `HEAD` with its merge base against `main`, else `master`, else the branch's tracking or PR base.
5. `asked_user`: none of the above yields a target or base, so ask.

### 2. Freeze the diff

Write the change under review to `scope.patch`:

- branch: `git diff <base>...HEAD`
- commit range: `git diff <range>`
- PR: `gh pr diff <number>` when available, otherwise the branch diff of the PR head against its base
- working tree: `git diff HEAD`, plus `git diff --no-index /dev/null <file>` for each untracked file from `git ls-files --others --exclude-standard`
- files: `git diff --no-index /dev/null <file>` for each file, so the whole file is under review

Record `review_files` (every path in the patch, minus `exclude`), `base_sha`, `head_sha`, and `patch_sha256`. Always exclude `.review/**`.

### 3. Context package

List in `context_files` every file outside the patch that a reviewer needs to judge the change: callers of changed functions, the types and interfaces they use, the existing tests for the changed behaviour, and config that changes runtime behaviour. Give each a one-line `why`. Reviewers read these for understanding; findings stay anchored in `review_files`.

### 4. Intent

Steps 1 to 3 never wait on intent: `scope.patch` is already on disk and the context list drafted when you reach this step, so any question you ask can cite the frozen diff. Only `scope.json` waits for the answer.

Write your **best reading** as one clear paragraph stating what the change is meant to do, drawn from the user's message, commit messages, the PR description if one exists, and the code. Record which of those you used in `intent.sources`. Commit to one reading even when the sources conflict: a paragraph the user can accept or correct gets a faster, sharper answer than a menu of options.

Show the paragraph to the user before any reviewer starts:

- The user wrote the intent, or accepts your paragraph: `intent.status: confirmed`.
- The sources agree and leave nothing to interpret: `inferred`, which the report flags.
- The sources conflict or leave a gap: below the paragraph, name each conflicting source in one line (for example, a PR description that promises one behaviour and a later commit that reverses it), then ask the user to confirm or correct the paragraph. Continue once they answer.

### 5. Write

Write `scope.json`, validate it, and compute `scope_sha256` from its bytes (`sha256sum`, or `shasum -a 256` on macOS). Every brief and artifact carries this hash.

Done when `scope.json` validates, `patch_sha256` matches `scope.patch`, and the intent is confirmed or recorded as inferred.

Re-running `scope` with a different target or intent changes `scope_sha256`, so `synthesize` excludes reviews made against the old scope. Tell the user which existing reviews that strands.

## Review Command

Every reviewer follows [`references/reviewer-contract.md`](references/reviewer-contract.md): findings anchored in `review_files`, judged against the intent, with evidence, returned as `lane-review.schema.json` JSON.

- **Single lane** (no `lanes`): the host is the reviewer. Follow the reviewer contract yourself for `model` (default: your own model), then write `<model>.json` with `lane.kind: host-native`.
- **Several lanes**: follow [`references/lanes.md`](references/lanes.md) to preflight, brief, dispatch, collect, and write one artifact per lane.

When the user runs separate hosts by hand (one `review` per host), each host is a single lane reading the same `scope.json`.

Done when every requested lane has exactly one `<model>.json` that validates, including lanes that failed, which record their `status`.

## Synthesize Command

Read every `<model>.json` in `feature_dir` and write `summary.json`:

1. **Accept** a review only when it validates, its `lane.status` is `complete`, and its `scope_sha256` equals the current hash of `scope.json`. List every other review in `excluded_reviews` with its reason, and every lane in `reviewers`.
2. **Merge** duplicate findings across accepted reviews; keep meaningful disagreement as separate findings or in `disagreements`.
3. **Number** merged findings `RF-001`, `RF-002`, … in severity order.
4. **Record** `sources` (the `lane.model_used` of every review that reported the finding; vote abstention depends on it), `agreement_count`, and `suggested_tests`.
5. Carry `intent` over from `scope.json`.

Render `summary.md` from `assets/templates/review_summary.md`, every checkbox unchecked.

Done when every accepted finding appears in exactly one `RF` entry with its `sources`, and every review file is either accepted or listed in `excluded_reviews`.

## Vote Command

Every voter follows the vote rules in [`references/reviewer-contract.md`](references/reviewer-contract.md): one vote per `RF` id, `abstain` on its own findings, evidence for every `confirm` and `dispute`, independent of other votes, returned as `lane-vote.schema.json` JSON.

- **Single lane**: the host votes as `model` and writes `<model>-vote.json`.
- **Several lanes**: follow [`references/lanes.md`](references/lanes.md), briefing each lane with `summary.json` and the same `scope.json`, and no other vote file.

After collecting, enforce abstention by `model_used`: a non-abstain vote on a finding whose `sources` contains the voter's `lane.model_used` becomes `abstain`, noted in `voter_notes`.

Done when every requested lane has one `<model>-vote.json` that validates, with one vote per `RF` id.

## Report Command

Every number in the report is deterministic, so a script computes it and you write only the prose:

1. **Compute.** Run `python3 -I <this skill dir>/scripts/report.py <feature_dir> [--weight MODEL=WEIGHT ...]`, one `--weight` per entry in `model_weights`. It reads `scope.json`, `summary.json`, and every `*-vote.json` (only `complete` votes on the current `scope_sha256` count), applies the rules below, and writes `final-report.json` with every score, bucket, agreement rate, flag, and missing voter filled in. Exit 1 means the inputs disagree (for example `summary.json` was made against an older scope): report its message to the user instead of computing by hand.
2. **Write the prose.** Fill `why_it_matters` for every `act_on` item, `tradeoff` for every `consider` item, `dismiss_rationale` for every `dismissed` item (drawn from the dispute evidence in the vote files), and `agreement_map.pattern`. Leave every number and bucket as the script wrote it.
3. **Validate and render** (below).

The rules the script applies, for writing prose that matches them:

### Confidence

- Resolve each model's weight from `model_weights`; unlisted models weigh `1.0`. Record the weights used.
- `confidence_score` = (sum of `confirm` weights + 0.5 × sum of `unsure` weights) ÷ (total weight of non-abstain votes).
- `confidence`: `high` when the score ≥ 0.7, `medium` when ≥ 0.4, `low` below 0.4.
- No non-abstain votes: `confidence: unvoted`, `confidence_score: null`.

### Buckets

Place each finding in the first bucket whose rule matches:

1. `unvoted`: `confidence` is `unvoted`.
2. `dismissed`: total `dispute` weight exceeds total `confirm` weight.
3. `act_on`: `confidence` is `high` and severity is `critical`, `high`, or `medium`; or severity is `critical` and `confidence` is `medium`.
4. `consider`: `confidence` is `medium`, or `confidence` is `high` with severity `low`.
5. `noted`: everything else.

Within each bucket, order by severity, then `confidence_score` descending. A bucket is a reading aid: every item stays unchecked, and only a human's checkbox approves a fix.

### Reviewers, flags, and agreement

- `reviewers` and `voters`: every lane, with its `status`, including failed ones. `missing_voters`: complete reviewers with no complete vote.
- `agreement_map.pairwise`: for each pair of voters, `shared_votes` counts findings both voted on without abstaining, and `agreement_rate` is the share of those where their votes match (`null` when none are shared). `same_vendor_agreement` and `cross_vendor_agreement` are the shared-vote-weighted means over same-vendor and cross-vendor pairs. `pattern` (yours to write) says where models agreed and diverged, and what that suggests about the findings; say so when pairs share too few votes to mean much.
- `report_flags`: `single_vendor` when complete lanes span fewer than two vendors; `intent_inferred` when `intent.status` is `inferred`; `missing_voters` when any are missing; `has_stand_ins` when any lane has `stand_in: true`.

Validate `final-report.json`, then render `final-report.md` from `assets/templates/final_report.md`, in the order Intent, Reviewers, Act On, Consider, Noted, Dismissed, Unvoted, Agreement Map, carrying checkbox states over by `RF` id.

Done when `final-report.json` validates, every number in it is the script's, and every `act_on`, `consider`, and `dismissed` item has its prose field filled.

## Lanes

A lane is one model at one effort, reached by one mechanism: a native subagent of the host's own vendor (`host:<model>`), the Codex CLI (`codex:<model>`), or the Claude Code CLI (`claude:<model>`). Read [`references/lanes.md`](references/lanes.md) whenever `lanes` is set or the user asks for a multi-model, cross-model, or cross-vendor review: it holds the lane spec, the default lane lists (newest models at `xhigh`), how model and effort map onto each mechanism, the exact CLI invocations, status mapping, and failure rules.

## Fix Rules

In `fix`:

1. Read the checked `RF` ids from `final-report.md` when it exists, otherwise from `summary.md`, and their details from the matching JSON.
2. Select only checked items whose status allows fixing.
3. Confirm the fix scope unless the user already explicitly approved it.
4. Create or update `fix-plan.md`.
5. Modify only the files the selected items need.
6. Run tests.
7. Update `status.md`.

When a checked item reveals a larger issue, stop and ask before widening the fix.

## Test Rules

Run tests after every fix batch, in this order:

1. The narrowest relevant test for the touched behaviour, when discoverable.
2. Typecheck, lint, or build checks relevant to the touched files.
3. The broader regression command, when discoverable and reasonably scoped.

When tests cannot run, record status `test_blocked`, the command that should have run, the blocking reason, and the residual risk.

When tests fail, mark the affected items `verification_failed` or `partially_fixed`, record the failing command, and summarize the failure. An item counts as fixed only with passing test evidence.

## Verification Rules

In `verify`:

- verify from a perspective independent of the fixer when possible;
- check whether each selected issue was actually addressed;
- rerun or inspect test evidence;
- look for regressions caused by the fix;
- update status only as far as the evidence supports.

Verification requires passing test evidence or a clear `test_blocked` explanation.

## Language Policy

Skill instructions, schema field names, and enum values stay in English. Prose fields in artifacts and rendered reports follow `report_language`: `auto` follows the user's prompt language; an explicit value sets it. Status display labels may be localized.

## Status Enums

Finding status values: `open`, `approved_for_fix`, `fixed`, `partially_fixed`, `wont_fix`, `risk_accepted`, `verified`, `verification_failed`, `test_blocked`. Each entry in a rendered report shows both `status` (the enum) and `status_label` (a localized label such as `Fixed ✅` or `已修復 ✅`).

Lane status values (`lane.status`): `complete`, `unavailable`, `timeout`, `invocation_error`, `schema_invalid`, `scope_mismatch`.

## Completion Criteria

A Review Forge workflow is complete only when:

- every artifact is under `feature_dir`, and every JSON artifact validates;
- every review and vote was made against the current `scope_sha256`;
- checked items are the only fixed items;
- test evidence or a `test_blocked` rationale is recorded after fixes;
- verification status claims only what its evidence shows;
- process artifacts remain isolated from product code.

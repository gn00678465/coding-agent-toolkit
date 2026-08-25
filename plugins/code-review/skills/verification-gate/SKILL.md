---
name: verification-gate
description: Use after code is written, when a change needs verifiable evidence instead of a claim that it works. Runs a constraint stack of executable layers (tests, types, lint, changed-line coverage, mutation, property-based tests, real execution, supply chain, suite health) against a change set, reconstructs RED for the new tests from the base ref, and ends with an evidence report the human can trust without opening a single source file. Use when the user asks to verify, prove, gate, or hand off finished work, or when the change touches money, auth, data loss, concurrency, or a public API. Not a code review skill — it does not read code looking for defects.
---

# Verification Gate

The human will NOT read your implementation. Their confidence comes entirely
from the **evidence report** you produce, proving the code ran the gate. Your
job is to make that report trustworthy enough that line-by-line review becomes
optional within the boundaries of what the gate actually measured.

This inverts the normal review model: **trust moves from inspection to
constraints.** Be honest about what that buys: the gate turns the constraints
the stated intent expresses into executable evidence — it cannot show the
stated intent expresses everything that matters, and it is not
self-authenticating, because a checker can be unsound and a mapping can claim
more than it demonstrates.

Upstream, `old-coder` closes the first gap with a spec the human approves
**before** code exists — the one artifact that breaks the
everything-authored-by-the-same-agent correlation. This skill runs after the
code is written, so that artifact may not exist. What replaces it is the
acquisition step below: read git for facts, ask the human once for intent, and
record honestly which of the two you got. Every shortcut you take against the
gate destroys the only basis of trust.

## Scope Boundary

This skill **does not review code**. It does not look for defects, does not
rank findings, and does not propose fixes. It runs checks and reports results.

When a review workflow is also in play (a human reviewer, a PR review bot), the
division is fixed: the review workflow owns
finding defects and deciding what to fix; this skill owns demonstrating that
the resulting change holds up. Do not run two parallel workflows. This skill
never reads or writes another workflow's artifacts; a review workflow's output
is one valid *source* of stated intent, never a required input.

## Commands

- `scaffold`: create or repair the gate entry point and its helper scripts in
  the target repository. Writes to product paths — always confirm first.
- `gate`: run the layers against the change set and report results. Iterative;
  use while fixing. Does not write an evidence report.
- `evidence`: run the entry point once and write the evidence report from that
  single run. This is the final step.

If the user does not specify a command, infer it: no entry point in the repo →
`scaffold`; entry point exists and the user wants results → `gate`; the user
wants a report, a handoff, or "prove it" → `evidence`.

## Inputs

Resolve or ask for these before doing work:

- `change_set`: what to verify. Working tree, `<base>...HEAD`, a commit range,
  or a PR. Default: uncommitted changes if any exist, otherwise `main...HEAD`,
  then `master...HEAD`.
- `base`: the ref the change is measured against. Needed for the changed-unit
  list, the baseline run, and RED reconstruction.
- `intent`: what the change was supposed to do. See Acquisition.
- `tier`: `1`, `2`, or `3`. See Calibration. Infer and state it; the human may
  override.
- `entry_point`: the single command that reruns every layer. Default: discover
  it in the repo, otherwise `scaffold` one.
- `artifact_root`: default `.gate/`.
- `scope`: subfolder name under `artifact_root`. Infer from branch name, PR
  title, or a short sanitized summary of the change.
- `report_language`: default `auto`, meaning follow the user's prompt language.

## Acquisition

The gate runs at a point that may be far from where the code was written: a
later session, a different agent, a subagent whose context is gone, or the far
side of a context compaction. It therefore takes **nothing on trust from the
conversation.** This mirrors a rule the upstream skill already applies to its
verifier, which receives an exact source state and an approved spec as inputs
and is told: never your conversation.

### From git — facts, always available in a repository

Settle all of this before asking the human anything:

| Fact | How |
|---|---|
| Change set | `git diff <base>...HEAD`, or the working tree diff |
| Changed units | derive from the diff: added/modified/deleted functions, methods, branches, exported symbols, config keys, endpoints, migration steps |
| Intent as recorded at the time | `git log <base>..HEAD` — commit messages are timestamped, authored when the code was written, and outside any transcript |
| Ordering | whether test files were committed before the implementation they cover |
| Baseline | check out `base` in a worktree and run the suite: which tests already failed before this change |
| Source state | `git rev-parse HEAD`, or a source-tree hash when git is absent |
| Spec provenance | `git log --diff-filter=A -- <path>` for any spec-like file, to see when it entered history |

None of this requires the original session. Compaction, subagent boundaries,
and session changes do not affect it.

### From the human — intent and authority

Ask **once**, after git has been read, and ask with the derived answer already
filled in so the human is confirming rather than composing:

> From git, this change does A, B, C. The commit messages say "<...>".
> What was this change supposed to accomplish? Is there a spec, issue, or PR I
> should read instead? Are there constraints it must **not** violate?

A confirmation, a correction, or a path are all useful replies. Record the
reply verbatim in the report.

This question is not a formality. A human can spot a missing claim without
reading a single line of code — "you said it handles retry, what about the
timeout path?" — and it is the only mechanism in this skill that breaks the
correlation between the code's author and the intent it is checked against.

Prefer artifacts the human points at over anything reconstructed: a spec file
in the repo, `gh issue view <n>`, `gh pr view <n>`. An issue or PR body is
human-authored, timestamped, attributable, and outside the agent's context — a
stronger source than anything in a transcript.

### Never from the conversation

Do not treat conversation history, a compaction summary, or a subagent's return
message as the intent record. When context is thin an agent does not fail, it
**reconstructs**, and a reconstruction is indistinguishable from the real thing
in the finished report. Worse, the reconstruction is derived from the code that
was already written, so it describes what the code does rather than what it
should do, and every mapped row passes trivially.

If the conversation is the only lead, write it down as a proposal, show it to
the human, and use their answer. Unconfirmed, it is not intent.

### Intent status

Record one of these in the report header. Never promote one silently:

- `confirmed` — the human confirmed the intent this run, or pointed at a spec,
  issue, or PR that states it.
- `unconfirmed` — non-interactive run (CI, cron, headless). Intent derived from
  git only.
- `absent` — git yields no usable intent and no one is available to ask.

`unconfirmed` and `absent` do not block the gate. Every executable layer runs
regardless; those layers ask whether the code is self-consistent, which needs no
intent at all. What degrades is the mapping, and the report says so — the same
honest downgrade the upstream skill records as
`spec approval: not obtained (autonomous run)`.

## Calibration

Scale effort to blast radius, and say which tier you chose:

- **Tier 1 — trivial** (typo, comment, config value): full suite + lint. No new
  tests required, but state why the change is untestable or already covered.
- **Tier 2 — normal** (bug fix, small feature): every always-on layer, plus both
  mapping tables. Bug fixes MUST carry a test that fails against the base ref —
  the fix is not done until yesterday's bug is tomorrow's regression test.
- **Tier 3 — high stakes** (money, auth, data loss, concurrency, public API):
  start with a short **failure model**: list the ways this specific change can
  hurt (race condition, partial write, hostile input, overflow, unbounded
  growth, failed rollback…), and for each mode add a layer that can actually
  catch it — race/stress tests for concurrency, fuzzing for parsers, rollback
  rehearsal for migrations, benchmarks for latency budgets, API-compatibility
  checks for public libraries, contract tests for service boundaries,
  logging/metric assertions where silent production failure is a mode (full
  menu in `references/layers.md`). Mutation and coverage cannot substitute for
  these; the generic gate is the floor, not the ceiling. Then: property-based
  tests + mutation testing (tool-based if available) + adversarial pass — one
  explicit step trying to break the implementation with hostile inputs before
  declaring done. Failure modes deliberately not covered go in EVIDENCE as
  known limits. The adversarial pass shares the blind spots of whoever runs it.

## The Layers

Run every applicable layer. Scale to the task (see "Calibration"), but never
skip a layer silently — if a layer doesn't apply or a tool is unavailable,
record that in the evidence report with the reason.

| Layer | What it catches | How |
|---|---|---|
| Full test suite | regressions | project's test command, zero NEW failures (baseline note below) |
| Static types | whole classes of bugs | tsc / mypy / etc., zero new errors |
| Lint + format | latent bugs, drift | project's linter, zero new warnings |
| Coverage on changed lines | untested code paths | every changed/added line executed by a test; branch coverage where the tool supports it. Global % is vanity — changed-line coverage is the constraint. **This layer must exit nonzero when its threshold is missed** (`--cov-fail-under`, `diff-cover --fail-under`, equivalent): a layer that prints a percentage and exits 0 is a report, not a gate layer, and it will sit there green while coverage falls |
| Mutation testing | tests that assert nothing | **prefer the project's mutation tool** (mutmut, cosmic-ray, Stryker, PIT…), which generates mutants from the syntax tree and cannot silently skip one. No tool available? Manual mutation, per `references/mutation.md` — introduce 3–5 plausible bugs one at a time; the suite must kill every one; restore after. A hand-rolled runner must **prove it executed each mutant**: a runner that can report a kill it never ran inflates the score and no red gate will ever surface it |
| Property-based tests | edge cases you didn't imagine | for parsing, math, serialization, anything with invariants (round-trip, idempotence, ordering) — add hypothesis/fast-check properties |
| Complexity budget | unmaintainable output | new functions small and single-purpose; if a function needs a paragraph to explain, split it |
| Real execution | "passes tests, doesn't run" | actually run the app/CLI/endpoint once on a realistic input, not only the test harness |
| Supply chain & secrets | vulnerable/unnecessary deps, leaked credentials | when the dependency set changed: audit it (pip-audit / npm audit / govulncheck / cargo-audit) and check licenses; scan the diff for secrets; every new dependency must trace back to a justification in the intent record. Also eyeball the capability diff: did the change start using network / subprocess / filesystem / env it didn't before? |
| Suite health | flaky or order-dependent tests | run the suite in randomized order (pytest-randomly etc.); repeat suspected flakes. Every EVIDENCE number rests on the suite being deterministic — a flaky suite quietly invalidates the report |

Baseline note — on a repo with pre-existing failures, record the baseline
first (which tests already fail, verbatim) and hold the line at zero NEW
failures. Fixing unrelated pre-existing failures is scope creep: surface them,
don't silently "improve" them.

Mutation caveat — **kills are attributed to whichever test fails first**, so a
7/7 kill score validates the suite as a whole, not every layer in it. In Tier 3,
rerun the mutants against the property suite alone before claiming the
properties verify anything; survivors there mean the invariants have blind
spots (a common one: a one-sided invariant like "never exceeds limit" cannot
catch fail-closed bugs — pair it with the opposite bound).

Checker note — the gate is only as trustworthy as its checkers, and the
dangerous checker failure is fail-open: nothing crashes, the layer prints pass.
Off-the-shelf tools (pytest, mypy, tsc…) have earned their failure behavior;
home-grown checks — grep gates, custom scripts, the manual mutation runner —
have not, so two rules apply to them: (1) **fail closed** — a crash, an
unreadable input, an unexpected exit code, or an item silently skipped inside
gate code is a hard failure of the layer, never a pass; no `|| true`, no
`2>/dev/null`, no bare fallthrough. (2) **Prove it can fail before trusting
its pass**: run it once against a known-bad input (a negative control) and
watch it fail — the RED principle applied to checkers, exactly like the
throwaway mutant for an immediately-passing test. Record the control in
EVIDENCE. Be precise about what that buys: **a negative control proves one
known-bad case reaches the checker's failure path. It does not prove the
checker recognizes every violation of the constraint it claims to enforce.**
A grep gate can fail closed perfectly and still guard a spelling rather than
a behavior. When the gate's coverage is narrower than the rule it serves, say
so where the rule is written, rather than letting the rule imply more.

Prove a negative control is itself non-vacuous the same way you prove a test:
temporarily remove or break the defence it validates, and watch the control go
red. A control that passes with the defence removed is measuring nothing —
this is a one-time proof, not a permanent extra layer.

Equivalent-mutant note — with a mutation tool, a survivor is not automatically
a failure: some mutants are semantically equivalent to the original and cannot
be killed. Classify such survivors as "equivalent, because <reason>" in
EVIDENCE rather than adding a meaningless test to kill them — that would
violate anti-gaming rule 4. Before reporting any survivor as a real gap,
construct a concrete input on which the original and the mutant diverge; if you
cannot, it is equivalent. Hand-written mutants (the manual procedure) get no
such excuse: you chose them, so choose real bugs.

## Reconstructing RED

**A test you never saw fail proves nothing — it may be testing nothing.** The
original session watched its tests go red before writing the implementation;
this gate runs afterwards and cannot. Git makes it recoverable:

1. Create a worktree at `base`.
2. Copy in the test files added by this change, along with any new fixtures or
   helpers they need.
3. Run those tests. **They must fail.**
4. Record which failed, and how.

If a test passes against the base ref, it is either vacuous (fix it) or the
behavior already exists. **Don't just assert which — prove it**: break the
implementation with a one-off throwaway mutant, watch the test fail, restore.
Then record it as pre-existing behavior kept as regression armor.

Caveats, recorded when they apply:

- A test that fails on import or collection is a weaker RED than an assertion
  failure. Note it rather than counting it the same.
- Tests *modified* rather than added cannot be replayed this way. Handle them
  case by case and say so.
- **A fresh worktree contains no gitignored content**, so the gate often
  cannot run there until dependencies are rebuilt. Two outcomes are acceptable
  — rebuild and run there, or record why reconstruction was not possible.
  Never report green from a tree that never ran the suite.

## Entry Point

Persist one command that runs every layer in sequence and fails on the first
broken one (e.g. `tools/gate.sh`: tests+coverage → types → lint → mutation →
real execution). Start the script by deleting stale artifacts from previous
runs (old coverage data, report files) so no layer can accidentally read a
prior run's output — freshness by mechanism, not discipline. (Keep tool
databases that accumulate value, e.g. hypothesis's example store.) The "final
fresh run" IS this command; EVIDENCE cites it, and the human can rerun the
whole report with it. Pin dev-tool versions (requirements-dev.txt, package.json
devDependencies with exact versions, etc.) so the rerun uses the same gate.

Gate code itself must fail closed (see the checker note above): `set -e` at the
top, no `|| true`, no `2>/dev/null`, and spell out the exit-code cases of any
command whose codes are ambiguous.

Keep the assurance boundary explicit: application coverage and mutation target
the subject under test; do not widen them across every orchestration script by
default. For the entry point itself, bind execution to completion: maintain a
fixed expected-layer manifest, record each layer only after its commands
succeed, and audit the manifest before printing success. Do not use a heading
as evidence that a layer ran, and do not rely on `set -e` through `&&` or
another conditional context; handle the command status explicitly.

The entry point and its helpers live in **product paths** (`tools/`), not under
`artifact_root`. This is the one place this skill writes outside its own
artifact folder, and it is deliberate: a report citing a script that lives only
in a scratch directory or in the conversation is not reproducible. Confirm
these writes with the user.

Contract details, the manifest pattern, and fail-closed shell idioms are in
`references/entry-point.md`.

## EVIDENCE — the only thing the human reads after code

End with a report the human can trust without opening a single source file
(template in `assets/templates/evidence.md`):

- The stated intent, with each claim mapped to the test that verifies it, and
  the changed-unit list, with each unit mapped to the test that exercises it.
- Each gate layer: the command run, and its actual result (pasted numbers,
  not adjectives). "All 47 tests pass, changed-line coverage 100% (31/31
  lines), 5/5 manual mutants killed" — never "tests look good".
- All numbers must come from one final fresh run executed after the last code
  edit — results from mid-task runs are stale and must not be reported.
- The report must be reproducible from the repo alone: every command it cites
  (including the mutation script) must exist as a persisted file in the repo,
  not in a scratch directory or only in the conversation. Reproducible means:
  dev-tool versions pinned or recorded, one entry-point command that reruns
  every layer, and the source state identified (commit SHA, or a source-tree
  hash when git is absent).
- Layers skipped, and why.
- Anything that failed and how it was resolved, honestly. A gate you passed on
  the first try and a gate you fixed your way through are equally fine; a gate
  you quietly weakened is the only failure.

### The two mapping tables

**Table 1 — Changed unit → Test.** Rows are derived from the diff, not chosen.
Record the command that produced the changed-unit list; without it, the table
degrades into a narrative and loses the only property that makes it strong.
Include **deletions**: a removed function needs a row saying what shows nothing
depended on it. Pure renames, moves, and formatting are not units — collapse
them into one row marked `n-a`. Fillable at every intent status, `absent`
included.

**Table 2 — Stated claim → Test.** Rows come from the intent record. This is
where negative constraints live — a diff can never tell you what the code must
**not** do — along with Tier 3 failure-model rows. It carries confidence only
when intent status is `confirmed`; at `unconfirmed`, print it and label the
source as commit messages rather than human confirmation; at `absent`, omit it
and say why.

Status is one of: **pass / fail / unverified / n-a**. A row mapped to
"skipped: <reason>" must carry unverified or n-a — never pass.

### Layers not run as specified

Split by status, because they mean different things to a reader:

- **N-A (this project has no such surface)**
- **UNAVAILABLE (tool missing, nothing run in its place)**
- **SUBSTITUTED (something else ran — and what it cannot detect)**

One "skipped" list collapses three states a reader has to tell apart: there is
no such surface in this project, versus the surface exists but the tool was
missing and nothing ran, versus something else ran and here is what it cannot
detect. Those are very different confidence claims and they read identically as
"skipped". The third is the dangerous one: **`SUBSTITUTED` may never be written
as a pass.** Two repeat runs in place of randomized order is not "suite health:
stable" — it is `SUBSTITUTED (2 repeat runs — cannot detect whole-suite order
dependence)`. A reader who cannot tell a substitute from the real layer reads
"found nothing" where the truth is "did not look with that instrument". `N-A`
is not a degraded run at all: three `N-A` layers describe the project, and
EVIDENCE should say so rather than leaving a reader to count absences.

### Dismissals and the blind spot

**Why dismissals need a line each.** A fix carries its own evidence — the test
that now passes. A dismissal carries none: "not a real problem" is
indistinguishable from "did not check". Name the command, `file:line`, or test
that disproves the finding — say what you tried, not only what you found.

**Why name the blind spot.** A layer a project cannot run at all otherwise
reads as absent rather than accepted. Stating it converts a silent gap into a
known limit the reader can price in.

## Anti-Gaming Rules (absolute)

The gate only creates trust if it cannot be gamed. These are hard rules:

1. **Never weaken a test to make it pass.** Don't broaden assertions, add skips,
   raise tolerances, or delete a failing test. If a test seems wrong, that's an
   intent conversation — surface it, don't bury it.
2. **Never edit a test and the implementation in the same step to reach green.**
   Change one, run, then the other. Simultaneous edits let you accidentally
   redefine correctness to match your bug.
3. **Never mock the unit under test** or mock so much that the test only
   exercises the mocks. Mock boundaries (network, clock, filesystem), not logic.
4. **Never chase the coverage number.** Coverage is a detector of untested code,
   not a target. A test added only to touch lines, with no meaningful assertion,
   is gaming — mutation testing exists precisely to catch this, including yours.
5. **Never report a layer you didn't run.** An honest "skipped: no mutation tool
   in this environment, did manual mutation instead" preserves trust; an
   invented result destroys the entire scheme.
6. **Failing gate blocks done.** You are not finished while any layer fails.
   If you're genuinely blocked, report the failure verbatim as the outcome.

## Setup

**Isolation — do not mutate the user's working tree to do your work.** Use a
worktree for the baseline run and for RED reconstruction. Where the isolated
tree and the tree the change lands in differ by ignored or untracked content,
say so in EVIDENCE: a green run in a tree missing the landing tree's `.env` or
build outputs is not evidence about the landing tree.

If the project has no test runner, no linter, or no type checking, set up the
minimal standard toolchain for the language **first** (see
`references/layers.md`). A gate can't run on bare ground. Setup changes the
user's environment — packages, config files, lockfiles — so confirm it before
doing it, and record every environment change actually made in the evidence
report. If the user forbids adding tooling, fall back to manual layers (manual
mutation, manual execution) and record the reduced confidence honestly.

If the directory is not a git repository, say so and stop before claiming any
provenance: acquisition, the baseline, and RED reconstruction all rest on git.
Offer `git init` and identify the source state with a tree hash instead of a
SHA.

## Artifacts

```text
.gate/<scope>/
  evidence.md      # the report
  baseline.md      # pre-existing failures at base, recorded verbatim
  red.md           # RED reconstruction results
```

Recommend adding `.gate/` to the target repository's `.gitignore` unless the
user wants the report committed; do not edit `.gitignore` unless asked. The
entry point and its helpers are **not** artifacts — they belong in `tools/`
and should be committed.

## Language Policy

Skill instructions, template field names, and status values are English.
Generated prose follows `report_language`: `auto` follows the user's prompt
language, explicit values such as `en`, `zh-TW`, or `ja` are allowed. Status
values stay English even inside a localized report.

## Completion Criteria

A verification gate run is complete only when:

- every applicable layer ran, or is recorded as `N-A` / `UNAVAILABLE` /
  `SUBSTITUTED` with a reason;
- every number came from one fresh run of a persisted entry point;
- intent status is recorded and was not silently promoted;
- Table 1 covers the changed-unit list, deletions included;
- no row mapped to a skip is marked `pass`;
- the structural blind spot is named;
- nothing is claimed that a reader cannot rerun.

## Attribution

The layer stack, the checker and mutation rules, the anti-gaming rules, and the
evidence report structure are adapted from the `old-coder` skill
(https://github.com/AmazingAng/old-coder, MIT, Copyright (c) 2026 amazingang).
See `NOTICE.md`.

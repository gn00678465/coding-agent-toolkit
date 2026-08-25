# Evidence Report — <task name> (Tier <1|2|3>)

- `command`: `evidence`
- `scope`: <!-- artifact subfolder name -->
- `change_set`: <!-- working tree | <base>...HEAD | commit range | PR -->
- `base`: <!-- comparison ref -->
- `report_language`: <!-- auto | en | zh-TW | ... -->
- `intent_status`: <!-- confirmed | unconfirmed | absent -->
- `intent_source`: <!-- human reply (verbatim) | spec file path | issue/PR ref |
  commit messages only -->
- `source_state`: <!-- commit SHA | no git: sha256 tree hash --> — persist the
  computation as a script (e.g. `tools/source_state.sh`); a hash recipe written
  in prose is working-directory-sensitive and will fail to reproduce. When Git
  exists, derive the tree hash from version-controlled inputs, fail on relevant
  staged, unstaged, deleted, or non-ignored untracked files, and never hash
  ambient ignored build artifacts. Checked before **and after** the final run
- `source_state_exclusions`: <!-- the verbatim whitelist of verifier paths the
  source-state check excuses (entry-point dir, artifact_root), or "none — the
  verifier is committed". Never a product path, never a blanket rule -->
- `toolchain`: <!-- pinned versions file, e.g. requirements-dev.txt -->
- `entry_point`: <!-- single command that reruns every layer -->
- `changed_unit_command`: <!-- the command that produced the changed-unit list -->
- `changed_unit_granularity`: <!-- symbol | path | module — what that command
  actually resolved to. `path` is acceptable when no symbol-level extractor
  exists for the ecosystem; leaving it unstated is not, because a path-level
  diff command and a real symbol extraction look identical in this header -->

## Baseline

Tests already failing at `base`, recorded verbatim before this change was
measured. The suite layer holds the line at zero NEW failures against this list.

<!-- verbatim list, or "none — base was green" -->

## Changed unit → Test

Rows are derived from the diff, not chosen. Include deletions. Pure renames,
moves, and formatting collapse into one `n-a` row.
At `path` or `module` granularity, state here what that leaves unmapped — e.g.
"rows are files; individual functions within a changed file are not
individually mapped".
Status is one of: **pass / fail / unverified / n-a**. A row mapped to
"skipped: <reason>" must carry unverified or n-a — never pass.

| Changed unit | Test | Status |
|---|---|---|
| <file>::<function/branch/symbol> | <test file>::<test name> | pass |
| deleted: <symbol> | <what shows nothing depended on it> | pass \| unverified |
| renames / moves / formatting (<n> files) | — | n-a |

## Stated claim → Test

Rows come from the intent record. Negative constraints live here — a diff can
never tell you what the code must not do. Omit this table entirely when
`intent_status` is `absent`, and say why.

| Claim | Test | Status |
|---|---|---|
| <what the change was supposed to do> | <test file>::<test name> | pass |
| Must NOT: <negative constraint> | <test / layer / skipped: reason> | pass \| unverified |

## RED reconstruction

New tests replayed against `base`. A test that passed there is either vacuous
or covers pre-existing behavior — say which.

| Test | Result at base | Note |
|---|---|---|
| <test file>::<test name> | failed (assertion) | — |
| <test file>::<test name> | failed (collection error) | weaker RED than an assertion failure |
| <test file>::<test name> | passed | pre-existing behavior, kept as regression armor |

<!-- or: "not performed — <reason>" -->
<!-- or: "NOT EVIDENCE (base lacks the platform under test) — every new test
     failed at collection because the project/package/toolchain itself is
     absent at base, which demonstrates nothing about whether any of them can
     fail when the behaviour breaks. <n>/<total> failed this way." Then record
     the substitute if one was run: per-test throwaway mutant against HEAD,
     which shows the test can fail but not that it failed before the code
     existed. -->

## Gate (final fresh run)

All numbers below come from one run of `entry_point` executed after the last
code edit. Paste actual numbers, never adjectives. This rule scopes to this
table: Baseline and RED reconstruction are runs against the base ref and cannot
come from it. Diagnostics from earlier runs belong in Honest notes, marked as
not from the final run — never in a cell here.

| Layer | Command | Result |
|---|---|---|
| Tests | <cmd> | <N> passed, 0 failed (baseline: <N> pre-existing) |
| Types | <cmd> | 0 errors |
| Lint | <cmd> | 0 warnings |
| Changed-line coverage | <producer cmd> + <gate cmd> | <covered>/<executable> changed executable lines; <n> not executable; **<n> executable with no coverage mapping** (list any misses; an unmapped count above zero caps what this layer can claim) |
| Mutation | <tool or "manual"> | <killed>/<total> killed; execution proved by <check> |
| Property-based | <cmd> | <N> properties, <examples/property> examples each |
| Complexity budget | <how checked> | <observed> |
| Real execution | <cmd> | <observed output> |
| Supply chain | <cmd> | 0 known vulns; new deps: none (or list, each ↔ justification) |
| Suite health | <cmd> | randomized order (seed <n>), all passed |

## Negative controls

Home-grown checks are only trusted after being seen to fail. One line each.

- <check> — fed <known-bad input>, failed as expected with <observed failure>
- <check> — proved non-vacuous by removing <defence> and watching the control go red
- (or "none — no home-grown checks in this gate")

## Layers not run as specified

Split by status, because they mean different things to a reader:

- **N-A (this project has no such surface):** <layer — why it does not exist here>
- **UNAVAILABLE (tool missing):** <layer — which tool, nothing run in its place>
- **SUBSTITUTED:** <layer — what ran instead, and what that cannot detect>
- **NOT REACHED (gate stopped at an earlier failing layer):** <layers — and
  which layer stopped the run>
- (or "none")

`SUBSTITUTED` may never be written as a pass. Neither may `NOT REACHED`: a
blocked gate is a finished run with a failing outcome, and every layer behind
the failure is unmeasured, not clean.

## Dismissed concerns

Fixes are self-evidencing; dismissals are not. One line each:

- <concern> — dismissed because <the command / file:line / test that disproves
  it>. <If the argument is "no alternative exists": which call sites it covers,
  and which it does not.>
- (or "none — every concern was fixed or accepted as a known limit")

## Structural blind spot

- <the layer this project cannot run at all, e.g. "the suite never exercises the
  container runtime, so nothing here is evidence about deployment behavior">

## Honest notes

- <failures hit during the run and how they were resolved; environment changes
  made during setup; isolated-tree vs landing-tree differences; anything
  reducing confidence>

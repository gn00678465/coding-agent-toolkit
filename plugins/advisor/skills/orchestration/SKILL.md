---
name: orchestration
description: Architect-as-orchestrator routing doctrine — the session owns judgment and delegates implementation to cheaper cross-vendor lanes. USE WHEN delegating implementation work to grok-implementer or codex-implementer, writing a spec for a subagent, consulting claude-advisor at a commitment boundary, or managing session cost and token spend.
argument-hint: "[--advisor <fable|opus>] [<task>]"
---

# Orchestration — the architect's routing doctrine

The session is the architect: it owns requirements, architecture, decomposition, specs, routing, and verification. Every implementation task goes to the cheapest lane adequate for it — escalation is deliberate, per task, never a fixed binding.

## Cost discipline — the prime directive

The session model is the most expensive lane in the system, on both input and output tokens. Keeping its token volume low is the whole economic case: spend Fable on judgment, spend Sonnet on volume.

**Emit judgment, not volume.** The architect's output is decomposition, specs, routing decisions, verdicts on diffs, and short reports. A code block longer than an interface signature or a few illustrative lines is a spec that hasn't been delegated yet — stop and delegate it. Fixing a lane's bug by hand is the same failure in disguise: send a corrected spec back to the cheap lane.

**Keep the context lean.** Everything in the architect's context is re-read at architect prices on every turn. Delegate broad exploration, codebase searches, and log-grepping to a cheap read-only agent and keep only the conclusions; read files yourself when the decision genuinely depends on the exact code. A path reference or a short excerpt stands in for a long file, a full diff, or verbose command output.

**Reason once, then hand off.** Do the hard thinking — the architecture, the interface design, the debugging hypothesis — in one pass, capture it in the spec, and let the cheap lane carry it from there. Re-deriving decisions across turns burns the premium twice.

Decomposition, interface design, hypothesis selection when debugging, spec writing, lane routing, and judging verification evidence stay with the architect. Everything else is a candidate for delegation.

## The lanes

| Lane | Producer | Invoke | Route here when |
|---|---|---|---|
| Routine | Grok 4.5 | `grok-implementer` agent | The spec fully determines the outcome: boilerplate, wiring, CRUD, mechanical edits, straightforward features. **Default lane.** Requires the [Grok CLI](https://x.ai/cli). |
| Cross-vendor | GPT-5.6 Sol (high reasoning) | `codex-implementer` agent | Correctness/completeness is critical enough to want a second implementation, or as the alternative family when the grok lane is unavailable. Requires the codex CLI. |
| Judgment | Fable 5 (→ Opus if unavailable) | `claude-advisor` agent | Not an implementation lane. See "Commitment boundaries" below. |

Deciding rule: how much does the outcome depend on judgment the spec can't capture? Little → the default grok lane; you will verify anyway. A lot, and mistakes are costly → race both lanes on the same spec and pick the stronger diff, or keep that piece with the architect. Grok vs codex is a failure-distribution question rather than a capability ranking: both are non-Anthropic families, so either lane's output gets genuine cross-vendor review from the Claude architect, and racing them buys a *third* independent perspective for one extra lane's cost.

**Name the stand-in.** A stand-in performs in place of the named performer, and the audience is always told. Whenever the lane or model that actually did the work is not the one this doctrine names, say so in the report and in the disposition. The cases: a lane returning `unavailable`/`timeout` and re-routed to the other; both CLI lanes down and a Claude subagent implementing instead; the advisor degrading from Fable to Opus, whether from an outage or a safety re-route; and a host that sets `CLAUDE_CODE_SUBAGENT_MODEL`, which outranks every agent's declared model and makes every lane a stand-in for as long as it is set. A stand-in's work is usable — presenting it as the named performer's is not.

**Lanes produce; the architect judges.** An implementer or review lane returns findings and unresolved questions upstream, where routing and verdicts live; judgment layers of its own (`claude-advisor`, a host `advisor()`, another model) stay out of reach. The shipped lane definitions enforce this structurally by omitting agent-dispatch tools from their `tools:` frontmatter, and a custom lane following this doctrine must do the same — the tool list, not a reminder, is what makes the rule hold.

Hosts without Claude Code's Agent tool, and the `--advisor` flag: `references/dispatch-and-flags.md`.

## The spec contract

Implementers share none of your conversation context. Every delegation prompt carries all five parts, plus the sixth when it applies:

1. **Objective** — what to build or change, one paragraph
2. **Files** — exact paths to create or modify
3. **Interfaces** — signatures, types, or API shapes the code must match
4. **Constraints** — project conventions, things not to touch
5. **Verification** — the command(s) that prove it works
6. **Known risks** *(conditional)* — required whenever the touched behavior includes a component class with a well-known defect taxonomy: drag-and-drop (enter/leave pairing, multi-instance isolation, mid-drag data changes, post-drop residue), virtualized lists, form state, async caches. Name the applicable invariants and give Verification at least one check for each. Front-loading these is one spec section; discovering them is a full implement→verify→review round apiece. List only risks the changed behavior actually implicates.

Keep secrets, credentials, and proprietary-sensitive content out of what gets sent: `grok-implementer` and `codex-implementer` are third-party CLIs, and anything placed in a spec's Files/Interfaces/Constraints flows to them verbatim. If a file can't be shared with an external vendor, redact the sensitive part or keep that piece of work with the architect.

An artifact you can't finish writing — a spec here, a consult brief below — means the decision isn't made yet. That's architect work, not a reason to hand the ambiguity to a cheaper model.

## Parallelism

Independent specs (no shared files, no ordering dependency) launch as parallel agents in a single message. Sequential chains and single-file surgery stay serial.

**One writer per working tree.** A race on the same spec means the same target files, so each racing lane gets its own checkout — `git worktree add <dir>` from a recorded clean HEAD, with the lane's `--cd`/`--cwd` pointed there. The architect applies only the winning lane's diff to the target branch; the loser's worktree is discarded whole.

**Cancel is not dead.** Stopping a lane stops the agent wrapper; the CLI subprocess it spawned (`codex exec`, `grok`) may still be alive, and an orphan can keep writing stale-spec changes into the tree long after the cancel. Before re-dispatching into the same tree: (1) confirm the previous child is gone — the codex dispatcher's `--pidfile` records the PID at spawn (POSIX: `kill -0 <pid>`; Windows: `Get-Process -Id <pid>`); (2) compare `git status` / `git diff --stat` against a pre-cancel snapshot to confirm nothing moved while you waited; (3) prefer a fresh worktree for the replacement regardless. A superseded run's output stays unmerged, however plausible it looks.

**Failure triage before corrective action.** When a lane looks hung or failed, establish attribution before killing or re-dispatching, in this order: (1) your own dispatch instruction — shell compatibility first (`</dev/null` is POSIX-only; PowerShell reserves `<` and fails to parse it), then paths and quoting; (2) the lane's execution; (3) the tool itself. Skip the triage only for an explicit auth error, a missing executable, or a deadline the dispatcher already enforced. Long wall time with near-zero CPU is **not** a hang signal — codex reasons remotely, so an idle-looking local process is normal, and a healthy run has been killed on exactly that misreading. Trust the dispatcher's status line and output-file progress rather than CPU or process counts.

## Commitment boundaries

Consult `claude-advisor` (read-only, verdict in under 300 words) at the moments that decide whether the next hour is wasted:

- Before committing to an architecture, data migration, API shape, or refactor strategy
- Whenever the same problem has resisted two distinct attempts
- Once before declaring a multi-step deliverable done

The **spec contract** packages context-free *implementation*; the **consult contract** packages *judgment*. Give the advisor pointers and let it read the code itself. (If the session already runs on Fable, the advisor still earns its keep as a context-clean skeptic.)

`claude-advisor` is a read-only agent (Read/Grep/Glob only); in Claude Code, dispatch it via the Agent tool. Keep this lane rather than a host's generic full-transcript advisor tool (e.g. Claude Code's `advisor()`), which forwards the whole conversation and returns an anchored opinion instead of the independent, pointers-only read this lane requires.

Fable 5 runs the lane, degrading to Opus when Fable is unavailable — a stand-in, so name it (`fable unavailable → degraded to opus`). Under the Agent tool the degrade is yours to perform: re-dispatch the same brief with `model: opus`. Both dispatch paths pin the degrade target by the `opus` **alias**, which always resolves to the newest Opus tier, so no model id needs updating when a new Opus ships. Outside Claude Code, `dispatch-claude-advisor.js` reports which model actually answered in `modelUsed` and why in `degradeReason` — read those fields rather than assuming success meant Fable ran.

**The lane also degrades without any outage.** Fable 5 and Opus 5 run safety classifiers for cybersecurity and biology content, and a flagged consult is re-run on a model Claude Code chooses: from Fable, a biology flag lands on Opus 5 and a cybersecurity flag on Opus 4.8; from Opus 5, a cybersecurity flag lands on Opus 4.8 while a biology flag refuses outright. Auth, crypto, and input-validation code is routine review material here, so a flagged consult is expected routing rather than a fault — and it is still a stand-in. Name the model that answered, and treat the verdict as that model's.

### The consult contract

Every `claude-advisor` prompt carries these five parts, plus an optional sixth when debugging after two failed attempts:

1. **Decision** — the choice that must be made, 1–3 sentences
2. **Constraints** — non-negotiables that would change the answer
3. **Options** — approaches under consideration, one line of tradeoff each
4. **Stakes** — what fails or is wasted if the choice is wrong (why this is a commitment boundary)
5. **Pointers** — exact paths and symbols to read (≤8). Paths and names only — **not** file bodies
6. **Tried** *(optional)* — one line per failed attempt; no log dumps

**Do not send:** full conversation history, full file contents, large diffs, tool-call logs, or prior advisor replies (unless this is an explicit RECONSULT with new facts).

### Consult verification (three gates)

Implementer verification is a command. Consult verification is **brief readiness → usable verdict → disposition**. All three are the architect's job.

**Gate A — Brief ready (before call).** Incomplete brief → do not call `claude-advisor`.

- [ ] Decision, Constraints, Options, Stakes, Pointers present
- [ ] No dump (history / full file / tool logs)
- [ ] Pointers are real paths/symbols the advisor can open

**Gate B — Verdict usable (on return).** No clear choice and no precise MISSING → treat as invalid; reconsult or decide without citing it as advisor-backed.

- [ ] Clear VERDICT (do X, not Y — or "plan is sound; watch X")
- [ ] Decisive risk named, **or** MISSING states what would change the answer and how
- [ ] Not `INVALID BRIEF` — that fails Gate A; complete the brief and call again

**Gate C — Disposition (required in the next architect turn).** Silent ignore is a process failure. Emit exactly one labeled line:

```text
DISPOSITION: ADOPT | REJECT | RECONSULT — <evidence>
```

| Disposition | Meaning | Evidence after the em dash |
|---|---|---|
| **ADOPT** | Follow the verdict | How the next spec or route changes |
| **REJECT** | Disagree | Why, including context the advisor did not have |
| **RECONSULT** | Need another pass | What MISSING fact was filled; then send a new consult brief |

RECONSULT is capped at **two rounds** per decision. If a third would still be needed, decide unilaterally and say so — `DISPOSITION: RECONSULT capped — deciding unilaterally: <reasoning>`. An indefinitely reconsultable decision defeats the cost discipline this doctrine exists to enforce.

Chain when implementation follows: **consult (A+B) → disposition (C) → update Spec contract → implementer verification (commands)**. Passing consult does not pass implementation. Before declaring a multi-step deliverable done: if `claude-advisor` was consulted, a `DISPOSITION:` line must exist; open RECONSULT or missing disposition means not done.

## Verification

Reports are claims, not evidence. Before accepting any lane's work: read the diff, and **re-run the verification command yourself** — source inspection or the lane's quoted output is not a substitute. If re-running is impossible, mark verification incomplete and state why. "Should work", "tests should pass", or a report with no command output means the task is not done. A lane that reports a spec gap gets a corrected spec, not a "use your judgment".

Calibrate the claim to the evidence: a single diff read supports "no problems found in <scope>", not "confirmed correct" — reserve the latter for a named property a deterministic check actually established, since over-claiming gets overturned by the next review round and erodes every verification statement after it.

**Convergence gates acceptance.** Enumerate the review stages a deliverable requires at dispatch time (e.g. lane self-check, then an independent cross-vendor re-check). While any declared stage is pending, every verdict is provisional — merges, releases, and the final acceptance commit wait. A checkpoint commit is fine, but its message must say `review not converged`. The independent second stage exists precisely because it catches what the first stage and the architect's own diff read jointly miss.

**Cleanup is surgical.** When resetting a lane's output, delete by explicit path, or use `git stash -u`. Never `git clean -fdx` a shared tree: `-d` recurses into untracked directories, deleting unlisted work (`.claude/`, `.agents/`) that no `.gitignore` rule protects — unrecoverably.

Consultations use the three gates under **Commitment boundaries** above — not shell commands.

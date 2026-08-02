# Dispatching outside Claude Code, and the `--advisor` flag

Two branches most runs never take. Read this when the session is hosted somewhere other than Claude Code, or when `$ARGUMENTS` carries `--advisor`.

## Dispatching lanes outside Claude Code

`agents/*.md` are Claude Code subagent definitions — only Claude Code's Agent tool loads them. Inside a different CLI (Codex, Grok, any other shell), reach the lanes through the bundled scripts instead.

**claude-advisor** — `node "${CLAUDE_SKILL_DIR}/scripts/dispatch-claude-advisor.js" <briefFile> [model] [fallbackModel]`

Takes the already-written consult brief as its first argument. It reads `agents/claude-advisor.md` at runtime and passes the body as the CLI's `--system-prompt`, so the persona stays identical to the Agent-tool path. Prints one line of JSON:

```json
{"status":"complete","outputFile":"...","modelUsed":"claude-opus-5","degraded":true,"degradeReason":"credits_exhausted"}
```

Judgment on `outputFile`'s contents stays with the architect, exactly as after an Agent-tool dispatch.

`degradeReason` separates causes that look alike from the outside:

- `credits_exhausted` — the primary's balance ran out. That arrives as HTTP 429, which the CLI's `--fallback-model` does **not** cover, so the script retries on the fallback model itself.
- `safety_fallback` — a safety classifier flagged the consult and Claude Code re-ran it somewhere the script never named. Only detectable when that target differs from both models passed in; with the default `opus` fallback alias every target is also "an opus", so this case usually surfaces as `undetermined`.
- `undetermined` — the answer came from the model passed as `--fallback-model`. Both the CLI's availability fallback and a safety re-route produce exactly that, and nothing in the output tells them apart. Report it as undetermined; a guessed cause reads as evidence and isn't.

The credit retry exists only here. Under the Agent tool, credit exhaustion belongs to Claude Code, so the two dispatch paths fail differently.

Two traps on this path. A flagged request in non-interactive mode ends in a refusal instead of a re-route when `switchModelsOnFlag` is `false` in settings — the run completes and the refusal text lands in `outputFile`, so read the verdict before acting on `status`. And to find out whether local customizations are what trips the classifier, run the consult under `claude --safe-mode`, which drops CLAUDE.md, skills, MCP servers, and hooks while keeping git status and directory names.

**codex-implementer**, and any read-only codex review — `node "${CLAUDE_SKILL_DIR}/scripts/dispatch-codex.js" <specFile> [--mode implement|review] [--model <slug>] [--timeout <seconds>] [--cd <dir>] [--pidfile <path>]`

All `codex exec` invocations go through this script, on every host. The spec text is the whole prompt, but the process lifecycle is not simple, and the script owns what per-call reminders failed to own: it writes the spec to codex's stdin and closes the stream (an inherited open pipe makes `codex exec` wait forever for EOF), enforces the deadline in-process (no `timeout` binary dependency), kills the whole process tree on expiry or cancellation, and records the child PID at spawn so a re-dispatch can verify the previous run is dead.

It prints one line of JSON. `timeout` always means the script enforced its deadline; `invocation_error` always means codex itself failed. Read the status field rather than inferring from output.

**grok-implementer** — no script. `grok --prompt-file` reads the spec from a file, so there is no stdin hazard; build the invocation from the recipe in `agents/grok-implementer.md` (preflight check, CLI flags, timeout handling).

## Overriding the advisor model

`--advisor <fable|opus>` pins which model runs `claude-advisor` for one invocation, bypassing the Fable-first default — `/orchestration --advisor opus fix the checkout race`. Run the bundled parser and read its JSON line:

- POSIX: `sh "${CLAUDE_SKILL_DIR}/scripts/parse-args.sh" "$ARGUMENTS"`
- Windows: `pwsh -NoProfile -File "${CLAUDE_SKILL_DIR}/scripts/parse-args.ps1" "$ARGUMENTS"`

```json
{"advisorModel":"opus","userPrompt":"fix the checkout race"}
```

`userPrompt` is everything that isn't the matched `--advisor <model>` pair; treat it as ordinary task text. `advisorModel` pins the Judgment lane only — `fable` states the default explicitly, `opus` skips waiting for a Fable failure to trigger the degrade. Pass it as the per-invocation `model` parameter on the Agent tool dispatch, or as the `[model]` argument to `dispatch-claude-advisor.js`. Empty means Fable 5 with the usual degrade.

The implementation lanes have no equivalent flag: `grok-implementer` and `codex-implementer` are producers, so choosing between them is the Deciding rule's job. To force one for a single invocation, say so in the task text ("use grok-implementer for this", "race both lanes on this spec") — the architect reads that like any other constraint in the request.

This `$ARGUMENTS` convention is Claude Code–specific; Codex's skill spec documents no argument-passing mechanism, and `agents/openai.yaml` carries no equivalent. Under Codex or Grok, state the desired advisor model or implementer in the task text and read it from there.

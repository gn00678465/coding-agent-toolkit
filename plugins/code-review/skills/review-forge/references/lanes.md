# Lanes

How the host fans `review` and `vote` out to several models, including other vendors' models through their CLIs. Read this whenever `lanes` is set or the user asks for a multi-model, cross-model, or cross-vendor review.

A **lane** is one reviewer or voter: one model reached by one mechanism, producing one JSON artifact. The host owns every lane: it builds the brief, dispatches, validates, stamps, and writes. A lane only returns JSON.

## Lane spec

`lanes` is a comma-separated list of `<kind>:<model>[@<effort>]`:

| `kind` | Mechanism | Example |
| --- | --- | --- |
| `host` | A subagent of the host's own vendor (`host-native`) | `host:claude-opus-5-5@xhigh`, `host:gpt-6.1-sol@xhigh` |
| `codex` | OpenAI Codex CLI, `codex exec` | `codex:gpt-6.1-sol@xhigh` |
| `claude` | Claude Code CLI, `claude -p` | `claude:claude-opus-5-5@xhigh` |

Name models by their full ID, so the lane, its artifact file, and `sources` all carry the exact model that ran.

When the user asks for a multi-model review without naming lanes, use one lane per vendor on the newest models at `xhigh`:

- Claude Code host: `host:claude-opus-5-5@xhigh, codex:gpt-6.1-sol@xhigh`
- Codex host: `host:gpt-6.1-sol@xhigh, claude:claude-opus-5-5@xhigh`

### Model and effort per mechanism

| Mechanism | Model | Effort |
| --- | --- | --- |
| `host` on Claude Code (Agent tool) | `model` takes a family alias: `claude-opus-5-5` → `opus`, `claude-sonnet-5-5` → `sonnet`, `claude-haiku-5-5` → `haiku`, `claude-fable-5-1` → `fable`. The alias resolves to the newest model of that family. | `effort`: `low`, `medium`, `high`, `xhigh`, `max` |
| `host` on Codex (`spawn_agent`) | `model: gpt-6.1-sol` | `reasoning_effort: xhigh` |
| `codex` (`codex exec`) | `--model gpt-6.1-sol` | `-c model_reasoning_effort=xhigh` (`minimal`, `low`, `medium`, `high`, `xhigh`, `max`) |
| `claude` (`claude -p`) | `--model claude-opus-5-5` (full ID or alias) | `--effort xhigh` (`low`, `medium`, `high`, `xhigh`, `max`) |

A lane with no `@<effort>` passes no effort and runs at the mechanism's default. `xhigh` runs take longer: when a CLI lane overruns the 600 s deadline, record `timeout` and tell the user, rather than lowering the effort on your own.

State the lane list before dispatching. The user may add, drop, or reweight lanes.

Give each lane a unique `label`, `<kind>-<model>` plus `-<perspective>` when one model runs several perspectives.

## Steps

### 1. Preflight

Check every CLI lane before dispatching any lane:

```bash
command -v codex && codex login status   # codex lanes; exit 0 means ready
command -v claude && claude auth status  # claude lanes; exit 0 means ready
```

A lane that fails preflight gets `status: unavailable` with the exact stderr as its reason, and is not dispatched. `host` lanes need no preflight.

Done when every lane is either ready or recorded as `unavailable`.

### 2. Briefs

For each ready lane, create `.review/<feature>/.lanes/<label>/` and write `brief.md` from `assets/templates/lane_brief.md`, filling `references/reviewer-contract.md` in verbatim. Compute `scope_sha256` once, from the bytes of `scope.json` (`sha256sum scope.json`, or `shasum -a 256 scope.json` on macOS), and put the same value in every brief. Use absolute paths for `output_schema`, `scope_file`, and `patch_file`.

Done when every ready lane has a `brief.md` whose `scope_sha256` matches the others.

### 3. Dispatch

Dispatch every ready lane in parallel, then wait for all of them.

**`host` lane, Claude Code host.** One Agent tool call per lane, all in a single message. Set the call's `model` to the lane model's family alias and `effort` to the lane effort (see the table above), use a general-purpose subagent, and send the full `brief.md` text as the prompt, ending with: `Return only the JSON document.`

**`host` lane, Codex host.** One `spawn_agent` per lane with `message` set to the full `brief.md` text, plus `model` and `reasoning_effort` from the lane spec. Collect each with `wait_agent`.

**`codex` lane.** One Bash call per lane, with the tool timeout at 660000 ms:

```bash
L=".review/<feature>/.lanes/<label>"
TO=$(command -v timeout || command -v gtimeout)
${TO:+$TO --kill-after=15s 600s} codex exec \
  --model "<model>" -c model_reasoning_effort="<effort>" \
  --sandbox read-only --ephemeral \
  --cd "$(git rev-parse --show-toplevel)" \
  --output-schema "<abs path>/assets/schemas/lane-<review|vote>.schema.json" \
  -o "$L/output.json" \
  - < "$L/brief.md" > "$L/stdout.txt" 2> "$L/stderr.txt"
echo "exit=$?"
```

Drop `-c model_reasoning_effort=...` when the spec gives no effort. The result is `$L/output.json`.

**`claude` lane.** One Bash call per lane, with the tool timeout at 660000 ms:

```bash
L=".review/<feature>/.lanes/<label>"
TO=$(command -v timeout || command -v gtimeout)
${TO:+$TO --kill-after=15s 600s} claude -p \
  --model "<model>" --effort "<effort>" \
  --tools "Read,Grep,Glob" --permission-mode dontAsk \
  --max-turns 40 --no-session-persistence \
  --output-format json \
  --json-schema "$(cat "<abs path>/assets/schemas/lane-<review|vote>.schema.json")" \
  < "$L/brief.md" > "$L/result.json" 2> "$L/stderr.txt"
echo "exit=$?"
```

Drop `--effort` when the spec gives none. The lane's JSON is `.structured_output` of `$L/result.json`; save it as `$L/output.json`. `--tools` limits the reviewer to reading; `dontAsk` denies anything else instead of waiting for a prompt nobody answers.

From a Codex host, `claude -p` needs network access to the Anthropic API, which Codex's default sandbox blocks. When stderr shows a network or sandbox error, mark the lane `unavailable` with that reason and tell the user it needs `network_access` or an approved escalation.

Without `timeout` or `gtimeout` (stock macOS), the run has no hard deadline; say so in the lane reason when it overruns.

Done when every dispatched lane has returned or hit its deadline.

### 4. Collect

For each lane, set `lane.status`:

| Condition | `status` |
| --- | --- |
| exit 124 or 137 under `timeout` | `timeout` |
| exit 127, or the CLI reports it is not logged in | `unavailable` |
| non-zero exit, or `claude` result has `is_error: true` | `invocation_error` |
| output does not validate against its schema (`<this skill dir>/scripts/validate.py`) | `schema_invalid` |
| output `scope_sha256` differs from the brief | `scope_mismatch` |
| otherwise | `complete` |

Then stamp the lane fields the reviewer could not know:

- `model_used`: the keys of `.modelUsage` for `claude` lanes; the requested model for `codex` and `host` lanes.
- `effort`: record the effort each lane ran at in `.lanes/<label>/`, next to its cost.
- `stand_in`: `true` when `model_used` is a different model family from `model_requested` (an alias resolving to its own full ID is the same model).

Write the artifact under the feature folder:

- `review`: `<model_used>.json`, or `<model_used>-<perspective>.json`; append the label when the name is taken.
- `vote`: `<model_used>-vote.json`.
- A lane that is not `complete` still gets its file, with its `status` and empty `findings` or `votes`, so the report can show it. Its raw output stays in `.lanes/<label>/`.

Done when every lane from the lane list has exactly one artifact file.

## Failure rules

- A failed lane stays failed. Each lane's file carries only that lane's own output: the host's own model writes under the host's model name, never under a failed lane's. Rerun a failed lane only when the user asks.
- A timed-out lane's partial output is never promoted into an artifact.
- Fewer than two vendors among `complete` lanes sets `single_vendor` in the report; fewer than two `complete` lanes means there is nothing to cross-vote, so report that to the user before `synthesize`.

## Cost

`claude` lanes report `total_cost_usd` in `result.json`; add `--max-budget-usd <n>` when the user sets a budget. Record each lane's cost and wall time in `.lanes/<label>/` and summarise them in `status.md` when the workflow reaches `fix`.

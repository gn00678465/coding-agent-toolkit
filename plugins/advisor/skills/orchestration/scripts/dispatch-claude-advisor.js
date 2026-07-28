#!/usr/bin/env node
// Dispatch the claude-advisor lane for hosts without Claude Code's Agent tool
// (e.g. a session running inside the Codex or Grok CLI itself).
//
// Usage:
//   node dispatch-claude-advisor.js <briefFile> [model] [fallbackModel]
//
// <briefFile> holds the full consult contract (Decision, Constraints, Options,
// Stakes, Pointers) — the caller writes it, this script only reads it.
// [model] / [fallbackModel] default to claude-fable-5 / opus.
//
// Prints exactly one line of JSON to stdout and always exits 0 — the caller
// reads the "status" field rather than the process exit code:
//   {"status":"complete","outputFile":"...","modelUsed":"claude-fable-5","degraded":false,"degradeReason":null}
//   {"status":"complete","outputFile":"...","modelUsed":"claude-opus-5","degraded":true,"degradeReason":"credits_exhausted"}
//   {"status":"timeout","outputFile":null}                        // this script's own deadline
//   {"status":"invocation_error","reason":"claude exited 1: ..."} // claude ran and failed
//   {"status":"unavailable","reason":"claude CLI not found on PATH"}
//
// On a degraded run, "degradeReason" says WHY the fallback answered:
// "credits_exhausted" (the primary's balance ran out) or "model_unavailable"
// (the CLI's own fallback fired on overload). Report it — the two mean
// different things to whoever reads the verdict.
//
// This script only dispatches and captures — it does not read the diff, does
// not re-run verification, and does not write a narrative report. That
// judgment stays with the calling architect, same as when this lane runs
// through Claude Code's Agent tool.

const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const TIMEOUT_MS = 600_000;
const MAX_BUFFER = 20 * 1024 * 1024;
const CREDITS_EXHAUSTED_STATUS = 429;

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

const briefFile = process.argv[2];
// The primary must be a full model name, not an alias: `degraded` below compares
// it against modelUsage's key, which is always the resolved canonical id — an
// alias here would report every successful run as degraded. The fallback has no
// such constraint, so it uses the `opus` alias to track the newest Opus tier.
const model = process.argv[3] || "claude-fable-5";
const fallbackModel = process.argv[4] || "opus";

if (!briefFile) {
  emit({ status: "unavailable", reason: "no brief file path given" });
  process.exit(0);
}

let brief;
try {
  brief = fs.readFileSync(briefFile, "utf8");
} catch (err) {
  emit({ status: "unavailable", reason: `cannot read brief file: ${err.message}` });
  process.exit(0);
}

// A fresh `claude -p` subprocess cannot resolve --agent claude-advisor by name
// (plugin agents loaded into the *calling* interactive session are not
// visible to a subprocess) — so the persona has to be supplied as an
// explicit system prompt. Read it from the same agent file the Agent-tool
// path uses, rather than duplicating its text here, so the two dispatch
// paths can't drift apart.
const agentFile = path.join(__dirname, "..", "..", "..", "agents", "claude-advisor.md");

let systemPrompt;
try {
  const raw = fs.readFileSync(agentFile, "utf8");
  systemPrompt = raw.replace(/^---\n[\s\S]*?\n---\n/, "").trim();
} catch (err) {
  emit({ status: "unavailable", reason: `cannot read agent persona file: ${err.message}` });
  process.exit(0);
}

const outputFile = path.join(os.tmpdir(), `claude-advisor-final-${process.pid}-${Date.now()}.txt`);

function tryParseJson(text) {
  if (!text) return null;
  try {
    return JSON.parse(text.toString());
  } catch {
    return null;
  }
}

function errorSuffix(parsed) {
  const status = parsed.api_error_status ? ` (HTTP ${parsed.api_error_status})` : "";
  const message = (parsed.result || parsed.error || "").toString().trim();
  return message ? `${status}: ${message.slice(0, 500)}` : status;
}

// Returns {ok: true, parsed} or {ok: false, payload, apiErrorStatus} — the
// payload is the exact object to emit, so the caller decides whether to retry
// without having to re-derive the diagnosis.
function runClaude(primaryModel, fallbackForRun) {
  const args = ["-p", brief, "--system-prompt", systemPrompt, "--model", primaryModel];
  if (fallbackForRun) args.push("--fallback-model", fallbackForRun);
  args.push("--allowedTools", "Read,Grep,Glob", "--output-format", "json", "--no-session-persistence");

  const startedAt = Date.now();
  let stdout;
  try {
    stdout = execFileSync("claude", args, { timeout: TIMEOUT_MS, maxBuffer: MAX_BUFFER, encoding: "utf8" });
  } catch (err) {
    // Attribution matters: a caller triaging a dead lane needs to know WHICH
    // failure happened, not a collapsed catch-all. "timeout" is reserved for
    // this script's own deadline; an externally-delivered signal or a non-zero
    // exit is an invocation_error.
    if (err.code === "ENOENT") {
      return { ok: false, payload: { status: "unavailable", reason: "claude CLI not found on PATH" } };
    }
    if ((err.killed || err.signal) && Date.now() - startedAt >= TIMEOUT_MS) {
      return { ok: false, payload: { status: "timeout", outputFile: null } };
    }
    if (err.killed || err.signal) {
      return {
        ok: false,
        payload: { status: "invocation_error", reason: `terminated by signal ${err.signal || "unknown"}` },
      };
    }
    // claude writes its own failure as JSON on stdout and leaves stderr empty,
    // so stdout is the only place the real cause lives. Never fall back to
    // err.message: execFileSync sets it to the whole command line, which
    // carries the system prompt and the brief verbatim.
    const failed = tryParseJson(err.stdout);
    const exited = `claude exited ${err.status ?? "abnormally"}`;
    if (failed) {
      return {
        ok: false,
        apiErrorStatus: failed.api_error_status ?? null,
        payload: { status: "invocation_error", reason: `${exited}${errorSuffix(failed)}` },
      };
    }
    const stderr = (err.stderr || "").toString().trim();
    return {
      ok: false,
      payload: {
        status: "invocation_error",
        reason: stderr ? `${exited}: ${stderr.slice(-500)}` : `${exited} with no diagnostic output`,
      },
    };
  }

  const parsed = tryParseJson(stdout);
  if (!parsed) {
    return { ok: false, payload: { status: "unavailable", reason: "claude returned non-JSON output" } };
  }
  // A zero exit code is not proof of success — claude can report the failure in
  // the payload instead. Without this check the error text would be written to
  // outputFile and returned as the advisor's verdict.
  if (parsed.is_error) {
    return {
      ok: false,
      apiErrorStatus: parsed.api_error_status ?? null,
      payload: { status: "invocation_error", reason: `claude reported an error${errorSuffix(parsed)}` },
    };
  }
  return { ok: true, parsed };
}

let outcome = runClaude(model, fallbackModel);
let degradeReason = null;

// The CLI's --fallback-model only fires when a model is overloaded or missing;
// an exhausted credit balance comes back as HTTP 429 and never triggers it. So
// the documented "degrade to Opus" would not hold for the failure operators
// actually hit most often — retry on the fallback here to close that gap.
if (
  !outcome.ok &&
  outcome.apiErrorStatus === CREDITS_EXHAUSTED_STATUS &&
  fallbackModel &&
  fallbackModel !== model
) {
  const retry = runClaude(fallbackModel, null);
  if (retry.ok) {
    outcome = retry;
    degradeReason = "credits_exhausted";
  } else {
    if (retry.payload.reason) {
      retry.payload.reason = `${model} out of credits; retry on ${fallbackModel} also failed — ${retry.payload.reason}`;
    }
    outcome = retry;
  }
}

if (!outcome.ok) {
  emit(outcome.payload);
  process.exit(0);
}

const modelUsage = outcome.parsed.modelUsage || {};
const modelUsed = Object.keys(modelUsage)[0] || model;
const degraded = modelUsed !== model;

fs.writeFileSync(outputFile, outcome.parsed.result || "");

emit({
  status: "complete",
  outputFile,
  modelUsed,
  degraded,
  degradeReason: degraded ? degradeReason || "model_unavailable" : null,
});

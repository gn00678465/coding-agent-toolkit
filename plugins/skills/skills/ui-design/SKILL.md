---
name: ui-design
description: Frontend UI design workflow backed by the impeccable skill. Use for any request to design, redesign, build, review, or refine a user interface, including small visual fixes such as spacing, layout, typography, color, or states (landing page, dashboard, settings page, component, form, onboarding, empty state, native screen), for creating or documenting a design system (PRODUCT.md, DESIGN.md, tokens), and for seeing or comparing UI variants. Runs the impeccable-ui-designer agent as a subagent where the harness supports it, or inline otherwise. Do not use for backend-only work, or when the user explicitly asks to run impeccable directly.
---

# UI Design (delegation)

This skill does not design anything itself. It sends the work to the **impeccable-ui-designer** subagent, which runs the impeccable skill in an isolated context. This session talks to the user: it passes the subagent's questions on and sends the answers back.

## 1. Find the subagent

| Harness | How to start it |
|---|---|
| Claude Code | Agent tool, `subagent_type: "impeccable-ui-designer"`. With a plugin install the type is `skills:impeccable-ui-designer`. Use the one listed as available. |
| Codex | Spawn the custom agent `impeccable-ui-designer` (defined in `.codex/agents/impeccable-ui-designer.toml`) and wait for it. |
| Pi with the `@tintinweb/pi-subagents` extension | Agent tool with `subagent_type: "impeccable-ui-designer"` and **`run_in_background: false`** (the default is background; always pass `false` so this session waits for the report). The Pi package of this repository declares the agent. Use it only when it is listed as an available agent type. |
| Pi without that extension, a harness without subagents, or any harness where `impeccable-ui-designer` is not an available agent type | Use **inline mode** (below), and say in the final summary that the work ran inline. |

### Inline mode (no subagents)

Read the agent definition with the read tool. Resolve each path from the skill location you were given, and use the first one that exists:

1. `<this skill's directory>/../../agents/impeccable-ui-designer.md`: the source, when the skill loads from the `skills` plugin (Claude Code plugin, Pi package of this repository) or was copied to `.claude/skills/`.
2. `<this skill's directory>/../../../.claude/agents/impeccable-ui-designer.md`: when the skill was copied to `.agents/skills/`.
3. `<this skill's directory>/../../../.codex/agents/impeccable-ui-designer.toml`: same, for a Codex-only setup. Follow its `developer_instructions` value.

Do not search the filesystem for it. If the read fails, tell the user and offer `/skill:impeccable <request>` instead. Otherwise, follow the agent definition in this session, with these changes:

- **Ask at gates.** Wherever the definition says to return `NEEDS_DECISION`, ask the user the same question with the same options, then stop and wait for the answer. Write no files before the user answers.
- **Live and generate are allowed here.** The user is in this session, so you may run `/skill:impeccable live` or `generate` with them, on web projects with a dev server on `localhost` or `https`.
- **Keep everything else.** Preflight, routing tree, craft floor, bounded verification, detector after the last write, no files outside the project, and the final report format all still apply.
- **Skip the parts about a parent agent.** Steps 2 and 3 below do not apply. End with the final report from the agent definition.

## 2. Write the brief

Send the user's request as close to verbatim as you can, and add only facts the user gave or the repository makes obvious:

```text
Task: <the user's request, verbatim>
Target: <files, routes, or components the user named, if any>
User-stated constraints: <stack, brand, fonts, palette, deadlines, "code it directly", etc.>
Answers to earlier questions: <from previous NEEDS_DECISION rounds, quoted>
```

Rules for the brief:
- **Do not answer the subagent's decision gates for the user.** Do not invent a direction, a mode, product facts, or "code-first, do not ask" unless the user said so.
- **Do not narrow or expand the scope.** A request to "fix the spacing" must not become "redesign the page".
- **Do not do design work in this session.** No CSS edits, no impeccable commands, no screenshots before the subagent reports.

## 3. Act on the report

The subagent always ends with a report whose first field is `Status`:

| Status | What this session does |
|---|---|
| `NEEDS_DECISION` | Ask the user each question with its options. In Claude Code, use AskUserQuestion when it is available. Elsewhere, ask in plain text and stop. Keep impeccable's pick and the category standard visible. When the user answers, resume the same subagent (Claude Code: SendMessage to its agent ID; Codex: send the answer to the same agent; Pi: the Agent tool with `resume` set to its agent ID) or start it again with the answers in the brief. |
| `DONE` | Summarize for the user: what changed (file paths), the key design decisions, the verification (viewports, detector results), waivers, assumptions, and context notices. Do not drop disclosures. Show screenshot paths from `.impeccable/review/` if the report lists them. Then offer the report's **Next** steps. |
| `BLOCKED` | Report the reason and the subagent's proposed fix. Ask the user how to proceed. |
| `SKILL_MISSING` | Tell the user that impeccable is not installed and give the install commands from the report. Stop. |
| Interim status, or no `Status` field | The subagent stopped early. Ask it once to finish and return its full final report. If it still does not, tell the user what is missing. |

## 4. Live preview and variants

The subagent never starts `live` or `generate`, because those need the user in the browser. When its report recommends them, or when the user wants to see variants:

1. Make sure a dev server runs on `localhost` or `https` (not a LAN IP). Web projects only: live and generate do not work on iOS, Android, or adaptive native projects.
2. Run it in **this** session with the user: `/impeccable live`, or `/impeccable generate <n> <action> <element>` (Codex: `$impeccable ...`; Pi: `/skill:impeccable ...`).
3. After the user accepts a variant, go back to delegation for further work.

## Install

- Subagent: `/plugin install skills@coding-agent-toolkit` in Claude Code. For Codex, copy `plugins/skills/.codex/agents/impeccable-ui-designer.toml` from this repository into the project's `.codex/agents/`.
- impeccable skill (required by the subagent): `npx impeccable install --providers=claude,codex`.

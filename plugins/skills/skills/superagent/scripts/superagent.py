#!/usr/bin/env python3
"""Superagent Router-Worker CLI helper with dual-layer stall & silent-hang watchdog.

Stdlib-only Python 3 script. Always invoke via `uv run`:
    uv run <skill-dir>/scripts/superagent.py <subcommand> ... --output <file>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows even under non-UTF-8 console codepages.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
VOLATILE_LINE_RES = [
    re.compile(r"^\s*[✻✶✳✢●·•]?\s*(Brewed|Sketching|Sautéed|Crunched|Churned|Worked|Thinking|Running)\b.*\d+[ms]", re.I),
    re.compile(r"Cache\s+\d+%\s+\d+:\d+", re.I),
    re.compile(r"\b\d+(\.\d+)?k/\d+(\.\d+)?[mk]\b", re.I),
    re.compile(r"^\s*[─━═\-]{10,}\s*$"),
    re.compile(r"\b5h:\s*[●○]+|\b7d:\s*[●○]+"),
]
INTERACTIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("permission_prompt", re.compile(r"Do you want to proceed|Allow once|Allow for this session|Permission required|Approve this", re.I)),
    ("yn_prompt", re.compile(r"\[y/N\]|\[Y/n\]|\(y/n\)|Press Enter to continue", re.I)),
    ("trust_or_auth", re.compile(r"Do you trust the files|trust this folder|Please login|Sign in to|Enter password|Enter passphrase", re.I)),
    ("quota_or_rate_limit", re.compile(r"rate limit|quota exceeded|usage limit|hit your limit|overloaded|try again at", re.I)),
]
PLACEHOLDER_RE = re.compile(r"<(?:SHA|commit SHA|結束碼|工作目錄|絕對路徑|階段)>|\bTBD\b|\bPLACEHOLDER\b")

DEFAULT_WATCHDOG = {
    "poll_cron": "*/3 * * * *",
    "state_stall_sec": 180,
    "prompt_stall_sec": 120,
    "silent_hang_sec": 600,
    "cpu_delta_epsilon_sec": 0.5,
    "repeat_cooldown_sec": 600,
    "max_alerts": 3,
    "dormant_idle_ticks": 5,
}

# dispatch 拒絕 model/effort 為空的角色：留空代表交給各 CLI 自己的預設，結果不可重現。
# codex 的值取自本機 ~/.codex/config.toml；agy 的 router 不經 dispatch，故不釘。
DEFAULT_ROLES = {
    "router": {"cli": "agy", "model": None, "effort": None},
    "brief": {"cli": "claude", "model": "opus", "effort": "high"},
    "brief-review": {"cli": "codex", "model": "gpt-6.1-terra", "effort": "high"},
    "impl": {"cli": "claude", "model": "opus", "effort": "high"},
    "fix": {"cli": "claude", "model": "opus", "effort": "high"},
    "review": {"cli": "codex", "model": "gpt-6.1-terra", "effort": "high"},
    "review-a": {"cli": "codex", "model": "gpt-6.1-terra", "effort": "high"},
    "review-b": {"cli": "codex", "model": "gpt-6.1-terra", "effort": "high"},
}
EFFORT_CHOICES = ["minimal", "low", "medium", "high", "xhigh", "max"]
# 同一階段從 base 重做（reset）的上限；超過即停機交給 Owner，不再自動重派。
DEFAULT_MAX_STAGE_RESETS = 2

ROLE_CHOICES = ["brief", "brief-review", "impl", "fix", "review", "review-a", "review-b"]
ALL_CONFIG_ROLES = ["router", *ROLE_CHOICES]


def utc_now(override_iso: str | None = None) -> datetime:
    if override_iso:
        dt = datetime.fromisoformat(override_iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def iso_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def emit_result(output_path: Path, payload: dict[str, Any], summary_lines: list[str], exit_code: int = 0) -> int:
    atomic_write_json(output_path, payload)
    for line in summary_lines:
        print(line)
    print(f"Output written to: {output_path.resolve()}")
    return exit_code


def workflow_dir(project: Path) -> Path:
    return project / ".workflow"


def load_config(project: Path) -> dict[str, Any]:
    cfg_path = workflow_dir(project) / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing workflow config: {cfg_path}. Run `init` first.")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def load_state(project: Path) -> dict[str, Any]:
    state_path = workflow_dir(project) / "state.json"
    if not state_path.exists():
        return {"version": 1, "active_stage": None, "idle_ticks": 0, "stages": {}, "workers": {}}
    return json.loads(state_path.read_text(encoding="utf-8"))


def save_state(project: Path, state: dict[str, Any]) -> None:
    atomic_write_json(workflow_dir(project) / "state.json", state)


def run_cmd(argv: list[str], cwd: Path | None = None, timeout: float = 15.0) -> dict[str, Any]:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "elapsed_sec": round(time.monotonic() - t0, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": f"Command timed out after {timeout}s",
            "elapsed_sec": round(time.monotonic() - t0, 3),
            "timed_out": True,
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "returncode": 127,
            "stdout": "",
            "stderr": str(exc),
            "elapsed_sec": round(time.monotonic() - t0, 3),
            "timed_out": False,
        }


def resolve_herdr_bin() -> str | None:
    return shutil.which("herdr-core") or shutil.which("hc")


def resolve_orca_bin() -> str | None:
    env_cmd = os.environ.get("ORCA_CLI_COMMAND")
    if env_cmd:
        return env_cmd
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        return shutil.which("orca-dev") or "orca-dev"
    if sys.platform.startswith("linux") and os.environ.get("TERM_PROGRAM") != "Orca":
        return shutil.which("orca-ide")
    return shutil.which("orca")


def _parse_ps_cputime(text: str) -> float:
    # [[dd-]hh:]mm:ss
    text = text.strip()
    if not text:
        return 0.0
    days = 0
    if "-" in text:
        d_str, text = text.split("-", 1)
        days = int(d_str)
    parts = [float(p) for p in text.split(":")]
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0.0, parts[0], parts[1]
    else:
        return 0.0
    return days * 86400.0 + h * 3600.0 + m * 60.0 + s


def inspect_process_tree(root_pid: int | None) -> list[dict[str, Any]]:
    if not root_pid or root_pid <= 0:
        return []
    if sys.platform == "win32":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            return []
        ps_script = (
            f"$root = {int(root_pid)}; "
            "$procs = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, CreationDate, CommandLine; "
            "$byParent = @{}; "
            "foreach ($p in $procs) { "
            "  $pp = [int]$p.ParentProcessId; "
            "  if (-not $byParent.ContainsKey($pp)) { $byParent[$pp] = New-Object System.Collections.ArrayList }; "
            "  [void]$byParent[$pp].Add($p) "
            "}; "
            "$byId = @{}; foreach ($p in $procs) { $byId[[int]$p.ProcessId] = $p }; "
            "$queue = New-Object System.Collections.Queue; "
            "if ($byId.ContainsKey($root)) { $queue.Enqueue($byId[$root]) }; "
            "$seen = @{}; $out = @(); "
            "while ($queue.Count -gt 0) { "
            "  $cur = $queue.Dequeue(); $cid = [int]$cur.ProcessId; "
            "  if ($seen.ContainsKey($cid)) { continue }; $seen[$cid] = $true; "
            "  $cpu = 0.0; "
            "  try { $gp = Get-Process -Id $cid -ErrorAction Stop; if ($null -ne $gp.CPU) { $cpu = [math]::Round([double]$gp.CPU, 3) } } catch {}; "
            "  $created = if ($cur.CreationDate) { $cur.CreationDate.ToUniversalTime().ToString('o') } else { $null }; "
            "  $out += [pscustomobject]@{ pid=$cid; ppid=[int]$cur.ParentProcessId; name=$cur.Name; cpu_sec=$cpu; created=$created; cmdline=$cur.CommandLine }; "
            "  if ($byParent.ContainsKey($cid)) { foreach ($ch in $byParent[$cid]) { $queue.Enqueue($ch) } } "
            "}; "
            "ConvertTo-Json -InputObject @($out) -Depth 4 -Compress"
        )
        res = run_cmd([shell, "-NoProfile", "-NonInteractive", "-Command", ps_script], timeout=10.0)
        if not res["ok"] or not res["stdout"].strip():
            return []
        try:
            data = json.loads(res["stdout"].strip())
            if isinstance(data, dict):
                return [data]
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    res = run_cmd(["ps", "-eo", "pid=,ppid=,comm=,cputime=,args="], timeout=8.0)
    if not res["ok"]:
        return []
    by_id: dict[int, dict[str, Any]] = {}
    children: dict[int, list[int]] = {}
    for line in res["stdout"].splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) < 4:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        entry = {
            "pid": pid,
            "ppid": ppid,
            "name": parts[2],
            "cpu_sec": round(_parse_ps_cputime(parts[3]), 3),
            "created": None,
            "cmdline": parts[4] if len(parts) > 4 else parts[2],
        }
        by_id[pid] = entry
        children.setdefault(ppid, []).append(pid)
    if root_pid not in by_id:
        return []
    queue = [root_pid]
    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    while queue:
        cid = queue.pop(0)
        if cid in seen or cid not in by_id:
            continue
        seen.add(cid)
        result.append(by_id[cid])
        queue.extend(children.get(cid, []))
    return result


def normalize_screen_lines(raw_text: str) -> tuple[list[str], str]:
    cleaned: list[str] = []
    stable: list[str] = []
    for raw in raw_text.splitlines():
        line = ANSI_RE.sub("", raw).rstrip()
        cleaned.append(line)
        if not line.strip():
            continue
        if any(pat.search(line) for pat in VOLATILE_LINE_RES):
            continue
        stable.append(line)
    digest = hashlib.sha256("\n".join(stable[-45:]).encode("utf-8", errors="replace")).hexdigest()
    return cleaned[-45:], digest


def detect_interactive_block(lines: list[str]) -> dict[str, str] | None:
    non_empty = [ln.strip() for ln in lines if ln.strip()][-25:]
    for ln in reversed(non_empty):
        for label, pat in INTERACTIVE_PATTERNS:
            if pat.search(ln):
                return {"pattern": label, "line": ln[:240]}
    return None


def check_report_marker(report_path: Path, expected_marker: str) -> tuple[bool, str | None]:
    if not report_path.exists() or not report_path.is_file():
        return False, None
    try:
        text = report_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, None
    markers = [m.strip() for m in expected_marker.split("|") if m.strip()]
    tail_lines = [ln.strip() for ln in text.splitlines() if ln.strip()][-20:]
    for ln in reversed(tail_lines):
        if ln in markers:
            return True, ln
    return False, None


def collect_logs_snapshot(watch_logs: list[str], stage_logs_dir: Path | None) -> tuple[list[dict[str, Any]], str]:
    targets: list[Path] = []
    seen: set[str] = set()
    for p in watch_logs:
        resolved = str(Path(p))
        if resolved not in seen:
            seen.add(resolved)
            targets.append(Path(p))
    if stage_logs_dir and stage_logs_dir.exists():
        log_files = sorted(stage_logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        for lf in log_files[:3]:
            key = str(lf)
            if key not in seen:
                seen.add(key)
                targets.append(lf)
    entries: list[dict[str, Any]] = []
    sig_parts: list[str] = []
    for path in targets:
        if path.exists() and path.is_file():
            st = path.stat()
            mtime_iso = iso_str(datetime.fromtimestamp(st.st_mtime, tz=timezone.utc))
            entries.append({"path": str(path), "exists": True, "mtime": mtime_iso, "size": st.st_size})
            sig_parts.append(f"{path}:{int(st.st_mtime)}:{st.st_size}")
        else:
            entries.append({"path": str(path), "exists": False, "mtime": None, "size": 0})
            sig_parts.append(f"{path}:missing")
    sig = hashlib.sha256("|".join(sorted(sig_parts)).encode("utf-8")).hexdigest()[:16]
    return entries, sig


def tail_file(path: Path, n: int = 20) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


def probe_worker(worker: dict[str, Any], cfg: dict[str, Any], mock_probes: dict[str, Any] | None = None) -> dict[str, Any]:
    wid = worker["id"]
    if mock_probes and wid in mock_probes:
        mp = dict(mock_probes[wid])
        raw_screen = mp.get("screen_text", "")
        screen_lines, screen_hash = normalize_screen_lines(raw_screen)
        tree = mp.get("process_tree", [])
        cpu_total = round(sum(float(p.get("cpu_sec", 0.0)) for p in tree), 3)
        return {
            "backend_ok": True,
            "backend_state": mp.get("backend_state", "live"),
            "agent_status": mp.get("agent_status", "working"),
            "status_msg": mp.get("status_msg", ""),
            "exit_code": mp.get("exit_code"),
            "pid": mp.get("pid"),
            "screen_lines": screen_lines,
            "screen_hash": screen_hash,
            "process_tree": tree,
            "subtree_cpu_sec": cpu_total,
            "interactive_match": detect_interactive_block(screen_lines),
        }

    backend = worker.get("backend", cfg.get("backend", "herdr"))
    ref = worker.get("backend_ref")
    if backend == "herdr":
        hbin = resolve_herdr_bin()
        if not hbin or not ref:
            return {"backend_ok": False, "error": "herdr-core binary or backend_ref unavailable"}
        get_res = run_cmd([hbin, "get", ref], timeout=10.0)
        if not get_res["ok"]:
            return {"backend_ok": False, "error": get_res["stderr"].strip() or "herdr-core get failed"}
        try:
            info = json.loads(get_res["stdout"])
        except json.JSONDecodeError:
            return {"backend_ok": False, "error": "Invalid JSON from herdr-core get"}
        read_res = run_cmd([hbin, "read", "--lines", "45", ref], timeout=10.0)
        screen_lines, screen_hash = normalize_screen_lines(read_res["stdout"] if read_res["ok"] else "")
        fg = info.get("foreground") or {}
        root_pid = fg.get("pid") or info.get("pid")
        tree = inspect_process_tree(root_pid)
        cpu_total = round(sum(float(p.get("cpu_sec", 0.0)) for p in tree), 3)
        st = info.get("status") or {}
        return {
            "backend_ok": True,
            "backend_state": info.get("state", "live"),
            "agent_status": st.get("state") or ("finished" if info.get("state") == "finished" else "working"),
            "status_msg": st.get("msg", ""),
            "exit_code": info.get("exit_code"),
            "pid": root_pid,
            "screen_lines": screen_lines,
            "screen_hash": screen_hash,
            "process_tree": tree,
            "subtree_cpu_sec": cpu_total,
            "interactive_match": detect_interactive_block(screen_lines),
        }

    if backend == "orca":
        obin = resolve_orca_bin()
        if not obin or not ref:
            return {"backend_ok": False, "error": "orca binary or dispatchId unavailable"}
        show_res = run_cmd([obin, "orchestration", "worker-show", "--dispatch", str(ref), "--json"], timeout=10.0)
        if not show_res["ok"]:
            return {"backend_ok": False, "error": show_res["stderr"].strip() or "orca worker-show failed"}
        try:
            info = json.loads(show_res["stdout"]).get("result") or {}
        except json.JSONDecodeError:
            return {"backend_ok": False, "error": "Invalid JSON from orca worker-show"}
        read_res = run_cmd([obin, "orchestration", "worker-read", "--dispatch", str(ref), "--source", "auto"], timeout=10.0)
        screen_lines, screen_hash = normalize_screen_lines(read_res["stdout"] if read_res["ok"] else "")
        liveness = str(info.get("liveness") or info.get("state") or "live").lower()
        backend_state = "live" if liveness in ("live", "ready", "active", "running") else "finished"
        agent_status = str(info.get("activity") or ("finished" if backend_state == "finished" else "working")).lower()
        interactive = detect_interactive_block(screen_lines)
        if not interactive and str(info.get("waitingOnHuman") or "").lower() in ("yes", "true", "waiting"):
            interactive = {"pattern": "orca_waiting_on_human", "line": f"waitingOnHuman={info.get('waitingOnHuman')}"}
        return {
            "backend_ok": True,
            "backend_state": backend_state,
            "agent_status": agent_status,
            "status_msg": f"{info.get('stage', '')} {info.get('lastActivity', '')}".strip(),
            "exit_code": None,
            "pid": None,
            "screen_lines": screen_lines,
            "screen_hash": screen_hash,
            "process_tree": [],
            "subtree_cpu_sec": 0.0,
            "interactive_match": interactive,
        }

    return {"backend_ok": False, "error": f"Unknown backend: {backend}"}


def send_nudge(worker: dict[str, Any], cfg: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    backend = worker.get("backend", cfg.get("backend", "herdr"))
    ref = worker.get("backend_ref")
    msg = (
        f"[watchdog] 檢查到階段 {worker['stage']} 尚未在 {worker['report_path']} 寫入完成標記 "
        f"`{worker['expected_marker']}`。請確認進度、完成剩餘驗證並在報告最後一行補上標記；若遇到阻塞請立即說明。"
    )
    if dry_run:
        return {"sent": True, "dry_run": True, "message": msg}
    if backend == "herdr":
        hbin = resolve_herdr_bin()
        if not hbin or not ref:
            return {"sent": False, "error": "herdr-core binary or backend_ref missing"}
        res = run_cmd([hbin, "send", ref, msg], timeout=10.0)
        return {"sent": res["ok"], "stderr": res["stderr"].strip(), "stdout": res["stdout"].strip()}
    if backend == "orca":
        obin = resolve_orca_bin()
        if not obin or not ref:
            return {"sent": False, "error": "orca binary or dispatch_id missing"}
        res = run_cmd(
            [obin, "orchestration", "send", "--to", f"dispatch:{ref}", "--subject", "Watchdog stall check", "--body", msg],
            timeout=10.0,
        )
        return {"sent": res["ok"], "stderr": res["stderr"].strip(), "stdout": res["stdout"].strip()}
    return {"sent": False, "error": f"Unknown backend: {backend}"}


# ----------------------------- Subcommands ----------------------------- #


def cmd_init(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not project.exists():
        print(f"Error: project path does not exist: {project}", file=sys.stderr)
        return 1
    wf = workflow_dir(project)
    cfg_path = wf / "config.json"

    if cfg_path.exists():
        # 既有設定是使用者的決定，init 不得覆寫；要改請用 set-role。
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        config_status = "existing"
    elif not args.use_defaults:
        # 腳本無法詢問人：停下來把預設值交給 Router，由 Router 問使用者後再帶 --use-defaults 重跑。
        payload = {
            "initialized": False,
            "error_code": "CONFIG_MISSING",
            "config_path": str(cfg_path),
            "defaults_preview": {"roles": DEFAULT_ROLES, "max_review_rounds": 3, "max_stage_resets": DEFAULT_MAX_STAGE_RESETS},
        }
        return emit_result(
            Path(args.output),
            payload,
            [
                f"No config at {cfg_path}. Ask the Owner to confirm roles (cli/model/effort), or rerun with --use-defaults.",
                "Adjust afterwards with `set-role`.",
            ],
            exit_code=3,
        )
    else:
        config_status = "created_defaults"
        cfg = None

    wf.mkdir(parents=True, exist_ok=True)
    artifacts_dir = Path(cfg["artifacts_dir"]) if cfg else (Path(args.artifacts_dir).resolve() if args.artifacts_dir else (wf / "stages"))
    logs_dir = Path(cfg["logs_dir"]) if cfg else (Path(args.logs_dir).resolve() if args.logs_dir else artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if cfg is None:
        cfg = {
            "version": 1,
            "project_name": project.name,
            "project_root": str(project),
            "backend": args.backend,
            "herdr_space": args.herdr_space or project.name,
            "artifacts_dir": str(artifacts_dir),
            "logs_dir": str(logs_dir),
            "max_review_rounds": 3,
            "max_stage_resets": DEFAULT_MAX_STAGE_RESETS,
            "watchdog": dict(DEFAULT_WATCHDOG),
            "roles": dict(DEFAULT_ROLES),
        }
        atomic_write_json(cfg_path, cfg)
    state_path = wf / "state.json"
    if not state_path.exists():
        save_state(project, {"version": 1, "active_stage": None, "idle_ticks": 0, "stages": {}, "workers": {}})

    # 設定與狀態含本機路徑，不得進 git。寫 .git/info/exclude 而非改使用者的 .gitignore。
    has_ignore = run_cmd(["git", "-C", str(project), "check-ignore", "-q", ".workflow/config.json"], timeout=5.0)["returncode"] == 0
    excluded_now = False
    if not has_ignore:
        ex = run_cmd(["git", "-C", str(project), "rev-parse", "--git-path", "info/exclude"], timeout=5.0)
        if ex["ok"]:
            ex_path = (project / ex["stdout"].strip()).resolve()
            ex_path.parent.mkdir(parents=True, exist_ok=True)
            with ex_path.open("a", encoding="utf-8") as fh:
                fh.write("\n.workflow/\n")
            has_ignore = excluded_now = True

    unpinned_roles = sorted(
        r for r in ROLE_CHOICES if not (cfg.get("roles", {}).get(r, {}).get("model") and cfg["roles"][r].get("effort"))
    )

    clis = {
        "herdr": resolve_herdr_bin(),
        "orca": resolve_orca_bin(),
        "claude": shutil.which("claude"),
        "codex": shutil.which("codex"),
        "agy": shutil.which("agy"),
        "uv": shutil.which("uv"),
        "git": shutil.which("git"),
    }
    payload = {
        "initialized": True,
        "config_status": config_status,
        "config_path": str(cfg_path),
        "state_path": str(state_path),
        "git_ignored": has_ignore,
        "added_to_git_exclude": excluded_now,
        "unpinned_roles": unpinned_roles,
        "detected_clis": clis,
        "config": cfg,
    }
    summary = [
        f"Superagent workflow for '{project.name}': config {config_status} (backend={cfg.get('backend')}).",
        f"Artifacts: {artifacts_dir} | Logs: {logs_dir}",
        f".workflow/ ignored by git: {has_ignore}" + (" (added to .git/info/exclude)" if excluded_now else ""),
    ]
    if unpinned_roles:
        summary.append(f"Unpinned roles (need model+effort via set-role): {', '.join(unpinned_roles)}")
    return emit_result(Path(args.output), payload, summary)


def cmd_stage_new(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    stage = args.stage.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", stage):
        print(f"Error: invalid stage name '{stage}'", file=sys.stderr)
        return 1

    stage_dir = Path(cfg["artifacts_dir"]) / stage
    logs_dir = Path(cfg["logs_dir"]) / stage / "logs"
    wd_dir = stage_dir / "watchdog"
    stage_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    wd_dir.mkdir(parents=True, exist_ok=True)

    base_ref = args.base
    if not base_ref:
        git_res = run_cmd(["git", "-C", str(project), "rev-parse", "--short", "HEAD"], timeout=5.0)
        base_ref = git_res["stdout"].strip() if git_res["ok"] else "HEAD"

    brief_path = stage_dir / "brief.md"
    report_path = stage_dir / "report.md"
    if not brief_path.exists() or args.force:
        brief_content = (
            f"# 階段 {stage}：實作 Brief\n\n"
            f"## Mandate（目標與邊界）\n"
            f"- **目標**：{args.goal}\n"
            f"- **起點（base）**：`{base_ref}`\n"
            f"- **專案目錄**：`{project}`\n"
            f"- **日誌目錄**：`{logs_dir}`（每份 `.log` 最後一行必須寫 `exit=<結束碼>`）\n\n"
            f"## 不變量與邊界條件\n"
            f"- （由 Router / Brief Worker 補齊具體不變量、允許修改範圍與禁止碰觸範圍）\n\n"
            f"## 報告與完成標記\n"
            f"- 報告寫至：`{report_path}`\n"
            f"- 全部驗證通過並 commit 後，在報告最後一行單獨寫上：\n\n"
            f"IMPL DONE\n"
        )
        brief_path.write_text(brief_content, encoding="utf-8")

    state = load_state(project)
    state["active_stage"] = stage
    prior = (state.get("stages") or {}).get(stage) or {}
    if str(prior.get("status", "")).startswith("halted"):
        print(f"Error: stage '{stage}' is halted; Owner must rule via `reset-stage --owner-ack`.", file=sys.stderr)
        return 1
    state.setdefault("stages", {})[stage] = {
        # 重建階段不得清掉重做計數，否則總停損可被繞過。
        **{k: prior[k] for k in ("reset_count", "reset_history") if k in prior},
        "stage": stage,
        "goal": args.goal,
        "base": base_ref,
        "round": 1,
        "status": "briefing",
        "stage_dir": str(stage_dir),
        "logs_dir": str(logs_dir),
        "brief_path": str(brief_path),
        "created_at": iso_str(utc_now()),
    }
    save_state(project, state)
    payload = {"stage": state["stages"][stage], "brief_created": True}
    return emit_result(
        Path(args.output),
        payload,
        [f"Stage '{stage}' ready (base={base_ref}).", f"Brief: {brief_path}"],
    )


def build_cli_argv(cli: str, brief_path: Path, cfg: dict[str, Any], model: str | None, effort: str | None) -> list[str]:
    prompt = f"讀 {brief_path.resolve()} 並照做。"
    artifacts_dir = str(Path(cfg["artifacts_dir"]).resolve())
    logs_dir = str(Path(cfg["logs_dir"]).resolve())
    if cli == "claude":
        argv = ["claude"]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--effort", effort]
        argv += ["--permission-mode", "auto", prompt]
        return argv
    if cli == "codex":
        argv = [
            "codex",
            "--no-daemon",
            "-s",
            "workspace-write",
            "-c",
            "sandbox_workspace_write.network_access=true",
            "--add-dir",
            artifacts_dir,
        ]
        if logs_dir != artifacts_dir:
            argv += ["--add-dir", logs_dir]
        if model:
            argv += ["-m", model]
        if effort:
            argv += ["-c", f'model_reasoning_effort="{effort}"']
        argv += ["-a", "never", prompt]
        return argv
    if cli == "agy":
        argv = ["agy", "--add-dir", artifacts_dir]
        if logs_dir != artifacts_dir:
            argv += ["--add-dir", logs_dir]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--effort", effort]
        argv.append(prompt)
        return argv
    return [cli, prompt]


def cmd_dispatch(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    state = load_state(project)
    backend = args.backend or cfg.get("backend", "herdr")

    role_cfg = (cfg.get("roles") or {}).get(args.role, {})
    cli = args.cli or role_cfg.get("cli") or "claude"
    model = args.model if args.model is not None else role_cfg.get("model")
    effort = args.effort if args.effort is not None else role_cfg.get("effort")

    stage_rec = (state.get("stages") or {}).get(args.stage) or {}
    if str(stage_rec.get("status", "")).startswith("halted"):
        payload = {"ok": False, "error_code": "STAGE_HALTED", "stage": args.stage, "halt": stage_rec.get("halt")}
        return emit_result(
            Path(args.output),
            payload,
            [f"Error: stage '{args.stage}' is halted ({stage_rec.get('status')}); Owner must rule via `reset-stage --owner-ack`."],
            exit_code=1,
        )

    unpinned = [k for k, v in (("model", model), ("effort", effort)) if not v]
    if unpinned and not args.allow_cli_default:
        payload = {"ok": False, "error_code": "ROLE_UNPINNED", "role": args.role, "cli": cli, "missing": unpinned}
        return emit_result(
            Path(args.output),
            payload,
            [f"Error: role '{args.role}' has no {'/'.join(unpinned)}; run `set-role` or pass --allow-cli-default."],
            exit_code=1,
        )

    brief_path = Path(args.brief).resolve()
    report_path = Path(args.report).resolve()
    if not brief_path.exists() and not args.dry_run:
        print(f"Error: brief file does not exist: {brief_path}", file=sys.stderr)
        return 1

    if not shutil.which(cli) and not args.dry_run:
        fallback = role_cfg.get("fallback")
        if fallback and shutil.which(fallback):
            cli = fallback
        else:
            payload = {"ok": False, "error_code": "CLI_MISSING", "cli": cli}
            return emit_result(Path(args.output), payload, [f"Error: CLI '{cli}' not found on PATH."], exit_code=1)

    workdir = Path(args.worktree).resolve() if args.worktree else project
    if backend == "herdr" and args.create_worktree_branch and not args.dry_run:
        if not args.worktree:
            print("Error: --create-worktree-branch requires --worktree <dir>", file=sys.stderr)
            return 1
        base = args.base or "HEAD"
        wt_res = run_cmd(
            ["git", "-C", str(project), "worktree", "add", "-b", args.create_worktree_branch, str(workdir), base],
            timeout=30.0,
        )
        if not wt_res["ok"]:
            payload = {"ok": False, "error_code": "WORKTREE_ERROR", "stderr": wt_res["stderr"]}
            return emit_result(Path(args.output), payload, [f"Failed to create worktree: {wt_res['stderr']}"], exit_code=1)

    worker_id = args.name or f"{args.role}-{args.stage}"
    watch_logs = [str(Path(p).resolve()) for p in (args.watch_log or [])]

    if backend == "herdr":
        hbin = resolve_herdr_bin() or "herdr-core"
        cli_argv = build_cli_argv(cli, brief_path, cfg, model, effort)
        cmd = [
            hbin,
            "run",
            "--bg",
            "--name",
            worker_id,
            "--cwd",
            str(workdir),
            "--label",
            f"herdr.space={cfg.get('herdr_space', project.name)}",
            "--label",
            f"herdr.tab={worker_id}",
            "--",
            *cli_argv,
        ]
    elif backend == "orca":
        obin = resolve_orca_bin() or "orca"
        wt_arg = "new-child" if args.create_worktree_branch else f"path:{workdir}"
        cmd = [
            obin,
            "orchestration",
            "worker-start",
            "--json",
            "--spec",
            f"讀 {brief_path} 並照做。",
            "--worktree",
            wt_arg,
            "--agent",
            cli,
        ]
        if wt_arg == "new-child":
            cmd += ["--name", worker_id]
        if model:
            cmd += ["--model", model]
        if effort:
            cmd += ["--effort", effort]
    else:
        print(f"Error: unsupported backend '{backend}'", file=sys.stderr)
        return 1

    if args.dry_run:
        payload = {
            "ok": True,
            "dry_run": True,
            "worker_id": worker_id,
            "backend": backend,
            "cli": cli,
            "model": model,
            "effort": effort,
            "workdir": str(workdir),
            "brief_exists": brief_path.exists(),
            "command": cmd,
        }
        return emit_result(Path(args.output), payload, [f"[dry-run] Would dispatch {worker_id} via {backend} ({cli})."])

    res = run_cmd(cmd, cwd=workdir, timeout=20.0)
    if not res["ok"]:
        payload = {"ok": False, "error_code": "BACKEND_ERROR", "command": cmd, "stderr": res["stderr"], "stdout": res["stdout"]}
        return emit_result(Path(args.output), payload, [f"Dispatch failed: {res['stderr'].strip()}"], exit_code=1)

    backend_ref = None
    try:
        parsed = json.loads(res["stdout"].strip())
        inner = parsed.get("result") if isinstance(parsed.get("result"), dict) else parsed
        backend_ref = inner.get("dispatchId") or inner.get("address") or inner.get("dispatch_id") or inner.get("id")
    except json.JSONDecodeError:
        m = re.search(r"\b(t[a-z0-9]{2,}|ctx_[A-Za-z0-9_-]+|dispatch:[A-Za-z0-9_-]+)\b", res["stdout"])
        backend_ref = m.group(1) if m else worker_id

    now_iso = iso_str(utc_now())
    worker_record = {
        "id": worker_id,
        "stage": args.stage,
        "role": args.role,
        "cli": cli,
        "model": model,
        "effort": effort,
        "backend": backend,
        "backend_ref": backend_ref,
        "workdir": str(workdir),
        "brief_path": str(brief_path),
        "report_path": str(report_path),
        "expected_marker": args.marker,
        "watch_logs": watch_logs,
        "status": "active",
        "started_at": now_iso,
        "last_progress_at": now_iso,
        "prompt_seen_since": None,
        "nudged_at": None,
        "last_probe": None,
        "alert_count": 0,
        "last_alert_sig": None,
        "last_alert_at": None,
        "last_incident_path": None,
    }
    state.setdefault("workers", {})[worker_id] = worker_record
    state["idle_ticks"] = 0
    if args.stage in state.get("stages", {}):
        state["stages"][args.stage]["status"] = f"running:{args.role}"
    save_state(project, state)

    payload = {"ok": True, "worker": worker_record, "command": cmd}
    return emit_result(
        Path(args.output),
        payload,
        [f"Dispatched '{worker_id}' via {backend} (ref={backend_ref}, cli={cli}).", f"Watching marker: {args.marker}"],
    )


def cmd_watch(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    state = load_state(project)
    wd_cfg = {**DEFAULT_WATCHDOG, **(cfg.get("watchdog") or {})}
    now = utc_now(args.now)
    now_iso = iso_str(now)

    mock_probes = None
    if args.mock_probe:
        mock_probes = json.loads(Path(args.mock_probe).read_text(encoding="utf-8"))

    events: list[dict[str, Any]] = []
    active_workers = [w for w in state.get("workers", {}).values() if w.get("status") == "active"]

    for w in active_workers:
        wid = w["id"]
        stage = w["stage"]
        stage_dir = Path(cfg["artifacts_dir"]) / stage
        stage_logs_dir = Path(cfg["logs_dir"]) / stage / "logs"
        report_path = Path(w["report_path"])

        # Layer 0: completion marker check
        marker_found, matched_line = check_report_marker(report_path, w["expected_marker"])
        if marker_found:
            w["status"] = "ready"
            w["completed_at"] = now_iso
            w["prompt_seen_since"] = None
            w["nudged_at"] = None
            events.append({
                "worker_id": wid,
                "stage": stage,
                "event": "READY_FOR_ROUTER",
                "tier": 0,
                "should_notify": True,
                "matched_marker": matched_line,
                "report_path": str(report_path),
            })
            continue

        # Probe backend + logs + process tree
        probe = probe_worker(w, cfg, mock_probes=mock_probes)
        logs_entries, log_sig = collect_logs_snapshot(w.get("watch_logs", []), stage_logs_dir)
        if not probe.get("backend_ok"):
            events.append({
                "worker_id": wid,
                "stage": stage,
                "event": "PROBE_ERROR",
                "tier": 2,
                "should_notify": True,
                "error": probe.get("error", "probe failed"),
            })
            continue

        prev = w.get("last_probe")
        screen_hash = probe["screen_hash"]
        cpu_now = float(probe["subtree_cpu_sec"])
        eps = float(wd_cfg["cpu_delta_epsilon_sec"])

        progressed = False
        if prev is None:
            progressed = True
        else:
            if screen_hash != prev.get("screen_hash"):
                progressed = True
            if log_sig != prev.get("log_sig"):
                progressed = True
            if (cpu_now - float(prev.get("subtree_cpu_sec", 0.0))) >= eps:
                progressed = True

        if progressed:
            w["last_progress_at"] = now_iso
            w["nudged_at"] = None
            w["alert_count"] = 0
            w["last_alert_sig"] = None
            w["last_alert_at"] = None

        interactive = probe.get("interactive_match")
        if interactive:
            if not w.get("prompt_seen_since"):
                w["prompt_seen_since"] = now_iso
        else:
            w["prompt_seen_since"] = None

        w["last_probe"] = {
            "checked_at": now_iso,
            "backend_state": probe["backend_state"],
            "agent_status": probe["agent_status"],
            "screen_hash": screen_hash,
            "log_sig": log_sig,
            "subtree_cpu_sec": cpu_now,
            "pid": probe.get("pid"),
        }

        last_prog_dt = parse_iso(w.get("last_progress_at")) or now
        stalled_sec = max(0, int((now - last_prog_dt).total_seconds()))
        prompt_dt = parse_iso(w.get("prompt_seen_since"))
        prompt_sec = max(0, int((now - prompt_dt).total_seconds())) if prompt_dt else 0

        event_type = "HEALTHY"
        tier = 0
        extra: dict[str, Any] = {}

        if probe["backend_state"] == "finished":
            event_type = "WORKER_EXITED_NO_MARKER"
            tier = 2
            extra["exit_code"] = probe.get("exit_code")
        elif interactive and prompt_sec >= int(wd_cfg["prompt_stall_sec"]):
            event_type = "INTERACTIVE_BLOCK"
            tier = 2
            extra["interactive_match"] = interactive
            extra["prompt_stalled_sec"] = prompt_sec
        elif probe["agent_status"] in ("done", "idle", "waiting") and stalled_sec >= int(wd_cfg["state_stall_sec"]):
            if not w.get("nudged_at") and args.auto_nudge:
                nudge_res = send_nudge(w, cfg, dry_run=bool(mock_probes))
                w["nudged_at"] = now_iso
                event_type = "AUTO_NUDGED"
                tier = 1
                extra["nudge_result"] = nudge_res
            else:
                event_type = "STATE_STALL_ESCALATE"
                tier = 1
                extra["already_nudged"] = bool(w.get("nudged_at"))
        elif probe["agent_status"] not in ("done", "idle", "waiting") and stalled_sec >= int(wd_cfg["silent_hang_sec"]):
            event_type = "SILENT_HANG"
            tier = 3

        if event_type in ("HEALTHY", "AUTO_NUDGED"):
            events.append({
                "worker_id": wid,
                "stage": stage,
                "event": event_type,
                "tier": tier,
                "should_notify": False,
                "stalled_seconds": stalled_sec,
                **extra,
            })
            continue

        # Anti-spam throttling for escalations
        sig = f"{wid}:{event_type}:{screen_hash[:12]}"
        if w.get("last_alert_sig") != sig:
            w["alert_count"] = 0
            w["last_alert_at"] = None

        max_alerts = int(wd_cfg["max_alerts"])
        cooldown = int(wd_cfg["repeat_cooldown_sec"])
        last_alert_dt = parse_iso(w.get("last_alert_at"))
        since_last_alert = int((now - last_alert_dt).total_seconds()) if last_alert_dt else cooldown + 1

        muted = w.get("alert_count", 0) >= max_alerts
        suppressed = (not muted) and (since_last_alert < cooldown)
        should_notify = (not muted) and (not suppressed)

        incident_path = None
        if should_notify:
            w["alert_count"] = int(w.get("alert_count", 0)) + 1
            w["last_alert_sig"] = sig
            w["last_alert_at"] = now_iso
            ts_tag = now.strftime("%Y%m%dT%H%M%SZ")
            inc_file = stage_dir / "watchdog" / f"{wid}_incident_{ts_tag}.json"
            incident_doc = {
                "timestamp": now_iso,
                "worker_id": wid,
                "stage": stage,
                "incident_type": event_type,
                "tier": tier,
                "alert_number": w["alert_count"],
                "stalled_seconds": stalled_sec,
                "backend": w.get("backend"),
                "backend_ref": w.get("backend_ref"),
                "backend_status": {
                    "state": probe["backend_state"],
                    "agent_status": probe["agent_status"],
                    "msg": probe.get("status_msg", ""),
                    "exit_code": probe.get("exit_code"),
                },
                "screen_tail": probe["screen_lines"][-40:],
                "watched_logs": [{**le, "tail": tail_file(Path(le["path"]), 20)} for le in logs_entries],
                "process_tree": probe["process_tree"],
                "extra": extra,
            }
            atomic_write_json(inc_file, incident_doc)
            incident_path = str(inc_file)
            w["last_incident_path"] = incident_path

        events.append({
            "worker_id": wid,
            "stage": stage,
            "event": event_type,
            "tier": tier,
            "should_notify": should_notify,
            "muted": muted,
            "suppressed_by_cooldown": suppressed,
            "alert_count": w.get("alert_count", 0),
            "stalled_seconds": stalled_sec,
            "incident_path": incident_path,
            **extra,
        })

    remaining_active = sum(1 for w in state.get("workers", {}).values() if w.get("status") == "active")
    if remaining_active == 0:
        state["idle_ticks"] = int(state.get("idle_ticks", 0)) + 1
    else:
        state["idle_ticks"] = 0
    should_sleep = remaining_active == 0

    save_state(project, state)
    notify_events = [e for e in events if e.get("should_notify")]
    payload = {
        "checked_at": now_iso,
        "active_workers": remaining_active,
        "should_sleep": should_sleep,
        "notify_count": len(notify_events),
        "events": events,
    }
    summary = [
        f"Watch tick @ {now_iso}: active={remaining_active}, alerts={len(notify_events)}, should_sleep={should_sleep}",
    ]
    for ev in notify_events:
        summary.append(f"  - [{ev['event']}] {ev['worker_id']} (tier={ev['tier']}) incident={ev.get('incident_path') or ev.get('report_path')}")
    return emit_result(Path(args.output), payload, summary)


def cmd_diagnose(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    state = load_state(project)
    w = (state.get("workers") or {}).get(args.worker)
    if not w:
        print(f"Error: worker '{args.worker}' not found in state.json", file=sys.stderr)
        return 1
    stage_logs_dir = Path(cfg["logs_dir"]) / w["stage"] / "logs"
    probe = probe_worker(w, cfg)
    logs_entries, log_sig = collect_logs_snapshot(w.get("watch_logs", []), stage_logs_dir)
    payload = {
        "timestamp": iso_str(utc_now()),
        "worker": w,
        "probe": probe,
        "log_sig": log_sig,
        "watched_logs": [{**le, "tail": tail_file(Path(le["path"]), 25)} for le in logs_entries],
    }
    summary = [
        f"Diagnosed worker '{w['id']}' (ref={w.get('backend_ref')}, ok={probe.get('backend_ok')}).",
        f"Process tree nodes: {len(probe.get('process_tree', []))}, total CPU={probe.get('subtree_cpu_sec', 0.0)}s",
    ]
    return emit_result(Path(args.output), payload, summary)


def cmd_verify_gate(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    report_path = Path(args.report).resolve()
    logs_dir = Path(args.logs_dir).resolve() if args.logs_dir else (Path(cfg["logs_dir"]) / args.stage / "logs")

    checks: list[dict[str, Any]] = []
    all_pass = True

    # 1. Report exists & marker present
    marker_ok, matched_line = check_report_marker(report_path, args.marker)
    checks.append({"name": "report_marker", "pass": marker_ok, "report": str(report_path), "matched": matched_line})
    all_pass = all_pass and marker_ok

    # 2. Placeholder check
    placeholder_hits: list[str] = []
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8", errors="replace")
        placeholder_hits = sorted(set(PLACEHOLDER_RE.findall(text)))
    ph_ok = report_path.exists() and len(placeholder_hits) == 0
    checks.append({"name": "no_placeholders", "pass": ph_ok, "hits": placeholder_hits})
    all_pass = all_pass and ph_ok

    # 3. Logs exit=0 check (mutation logs expected non-zero)
    log_files = sorted(logs_dir.glob("*.log")) if logs_dir.exists() else []
    bad_logs: list[dict[str, Any]] = []
    checked_logs: list[dict[str, Any]] = []
    if not log_files and not args.allow_empty_logs:
        checks.append({"name": "logs_present", "pass": False, "logs_dir": str(logs_dir)})
        all_pass = False
    else:
        for lf in log_files:
            lines = [ln.strip() for ln in lf.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
            last = lines[-1] if lines else ""
            m = re.fullmatch(r"exit=(-?\d+)", last)
            is_mutation = "mutation" in lf.name.lower()
            if not m:
                bad_logs.append({"file": str(lf), "reason": "missing final exit=<code> line", "last_line": last})
            else:
                code = int(m.group(1))
                expected_ok = (code != 0) if is_mutation else (code == 0)
                checked_logs.append({"file": lf.name, "exit_code": code, "is_mutation": is_mutation, "pass": expected_ok})
                if not expected_ok:
                    bad_logs.append({"file": str(lf), "exit_code": code, "is_mutation": is_mutation})
        logs_ok = len(bad_logs) == 0
        checks.append({"name": "logs_exit_codes", "pass": logs_ok, "checked": checked_logs, "failures": bad_logs})
        all_pass = all_pass and logs_ok

    # 4. Optional commit SHA check
    if args.commit:
        git_res = run_cmd(["git", "-C", str(project), "cat-file", "-e", f"{args.commit}^{{commit}}"], timeout=5.0)
        commit_ok = git_res["ok"]
        checks.append({"name": "commit_exists", "pass": commit_ok, "commit": args.commit})
        all_pass = all_pass and commit_ok

    payload = {"pass": all_pass, "stage": args.stage, "checks": checks}
    summary = [f"Verify-gate for stage '{args.stage}': {'PASS' if all_pass else 'FAIL'}"]
    for c in checks:
        summary.append(f"  - {c['name']}: {'ok' if c['pass'] else 'FAIL'}")
    return emit_result(Path(args.output), payload, summary, exit_code=0 if all_pass else 1)


def cmd_status(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    state = load_state(project)
    workers = list((state.get("workers") or {}).values())
    counts = {
        "active": sum(1 for w in workers if w.get("status") == "active"),
        "ready": sum(1 for w in workers if w.get("status") == "ready"),
        "closed": sum(1 for w in workers if w.get("status") == "closed"),
    }
    payload = {
        "project": cfg.get("project_name"),
        "backend": cfg.get("backend"),
        "active_stage": state.get("active_stage"),
        "max_review_rounds": cfg.get("max_review_rounds", 3),
        "max_stage_resets": cfg.get("max_stage_resets", DEFAULT_MAX_STAGE_RESETS),
        "roles": cfg.get("roles", DEFAULT_ROLES),
        "worker_counts": counts,
        "stages": state.get("stages", {}),
        "workers": [
            {
                "id": w["id"],
                "stage": w["stage"],
                "role": w["role"],
                "cli": w["cli"],
                "ref": w.get("backend_ref"),
                "status": w.get("status"),
                "last_progress_at": w.get("last_progress_at"),
                "alert_count": w.get("alert_count", 0),
                "last_incident_path": w.get("last_incident_path"),
            }
            for w in workers
        ],
    }
    summary = [
        f"Project '{payload['project']}' | stage={payload['active_stage']} | backend={payload['backend']}",
        f"Workers: active={counts['active']}, ready={counts['ready']}, closed={counts['closed']}",
    ]
    return emit_result(Path(args.output), payload, summary)


def cmd_set_role(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    roles = dict(cfg.get("roles") or DEFAULT_ROLES)
    entry: dict[str, Any] = {
        "cli": args.cli,
        "model": None if args.clear_model else (args.model if args.model is not None else roles.get(args.role, {}).get("model")),
        "effort": args.effort if args.effort is not None else roles.get(args.role, {}).get("effort"),
    }
    if args.fallback:
        entry["fallback"] = args.fallback
    roles[args.role] = entry
    cfg["roles"] = roles
    atomic_write_json(workflow_dir(project) / "config.json", cfg)
    payload = {"ok": True, "role": args.role, "assignment": entry, "roles": roles}
    return emit_result(
        Path(args.output),
        payload,
        [f"Updated role '{args.role}' -> cli={entry['cli']} (model={entry['model']}, effort={entry['effort']})."],
    )


def cmd_reset_stage(args: argparse.Namespace) -> int:
    """Count a from-base redo of a stage; halt instead of redoing once the cap is hit."""
    project = Path(args.project).resolve()
    cfg = load_config(project)
    state = load_state(project)
    stage = (state.get("stages") or {}).get(args.stage)
    if not stage:
        print(f"Error: stage '{args.stage}' not found", file=sys.stderr)
        return 1

    cap = int(cfg.get("max_stage_resets", DEFAULT_MAX_STAGE_RESETS))
    now_iso = iso_str(utc_now())
    history = stage.setdefault("reset_history", [])

    if args.owner_ack:
        if not str(stage.get("status", "")).startswith("halted"):
            print(f"Error: stage '{args.stage}' is not halted", file=sys.stderr)
            return 1
        stage["reset_count"] = 0
        stage["status"] = "briefing"
        stage["round"] = 1
        stage.pop("halt", None)
        history.append({"at": now_iso, "event": "owner_ack", "note": args.owner_ack})
        save_state(project, state)
        return emit_result(
            Path(args.output),
            {"ok": True, "stage": args.stage, "resumed": True, "reset_count": 0},
            [f"Stage '{args.stage}' resumed by Owner ruling; reset budget restored to {cap}."],
        )

    if str(stage.get("status", "")).startswith("halted"):
        payload = {"ok": False, "error_code": "STAGE_HALTED", "stage": args.stage, "halt": stage.get("halt")}
        return emit_result(Path(args.output), payload, [f"Error: stage '{args.stage}' already halted."], exit_code=1)

    if not args.reason:
        print("Error: --reason is required (what structural gap in the brief caused the round-3 failure)", file=sys.stderr)
        return 1

    count = int(stage.get("reset_count", 0))
    if count >= cap:
        stage["status"] = "halted:owner_required"
        stage["halt"] = {"at": now_iso, "reset_count": count, "cap": cap, "last_reason": args.reason}
        history.append({"at": now_iso, "event": "halt", "note": args.reason})
        save_state(project, state)
        payload = {"ok": False, "error_code": "STAGE_HALTED", "stage": args.stage, "halt": stage["halt"], "reset_history": history}
        return emit_result(
            Path(args.output),
            payload,
            [
                f"HALT: stage '{args.stage}' already reset {count}/{cap} times; no further automatic redo.",
                "Escalate to Owner with reset_history, then resume via `reset-stage --owner-ack \"<ruling>\"`.",
            ],
            exit_code=2,
        )

    stage["reset_count"] = count + 1
    stage["round"] = 1
    stage["status"] = "briefing"
    history.append({"at": now_iso, "event": "reset", "note": args.reason})
    save_state(project, state)
    return emit_result(
        Path(args.output),
        {"ok": True, "stage": args.stage, "reset_count": count + 1, "cap": cap, "reset_history": history},
        [f"Stage '{args.stage}' reset {count + 1}/{cap}; revise brief, drop old branch/worktree, redispatch."],
    )


def cmd_close_worker(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    cfg = load_config(project)
    state = load_state(project)
    w = (state.get("workers") or {}).get(args.worker)
    if not w:
        print(f"Error: worker '{args.worker}' not found", file=sys.stderr)
        return 1

    cleanup: dict[str, Any] = {}
    if w.get("backend") == "herdr" and w.get("backend_ref") and not args.skip_backend:
        hbin = resolve_herdr_bin()
        if hbin:
            cleanup["kill"] = run_cmd([hbin, "kill", w["backend_ref"]], timeout=8.0)
            cleanup["rm"] = run_cmd([hbin, "rm", w["backend_ref"]], timeout=8.0)

    if args.remove_worktree:
        wd = Path(w["workdir"]).resolve()
        if wd != project and wd.exists():
            cleanup["worktree_remove"] = run_cmd(
                ["git", "-C", str(project), "worktree", "remove", "--force", str(wd)],
                timeout=15.0,
            )

    w["status"] = "closed"
    w["closed_at"] = iso_str(utc_now())
    save_state(project, state)
    payload = {"ok": True, "worker_id": w["id"], "closed_at": w["closed_at"], "cleanup": cleanup}
    return emit_result(Path(args.output), payload, [f"Closed worker '{w['id']}'."])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Superagent Router-Worker orchestrator & watchdog CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="Initialize .workflow/ config and state in a project")
    sp.add_argument("--project", required=True)
    sp.add_argument("--backend", choices=["herdr", "orca"], default="herdr")
    sp.add_argument("--artifacts-dir")
    sp.add_argument("--logs-dir")
    sp.add_argument("--herdr-space")
    sp.add_argument("--use-defaults", action="store_true", help="Create the config from built-in defaults when none exists (Owner confirmed or declined to choose)")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("stage-new", help="Create a new stage folder and brief skeleton")
    sp.add_argument("--project", required=True)
    sp.add_argument("--stage", required=True)
    sp.add_argument("--goal", required=True)
    sp.add_argument("--base")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_stage_new)

    sp = sub.add_parser("dispatch", help="Dispatch a CLI worker and register it with watchdog")
    sp.add_argument("--project", required=True)
    sp.add_argument("--stage", required=True)
    sp.add_argument("--role", choices=ROLE_CHOICES, required=True)
    sp.add_argument("--cli", choices=["claude", "codex", "agy"])
    sp.add_argument("--model")
    sp.add_argument("--effort", choices=EFFORT_CHOICES)
    sp.add_argument("--allow-cli-default", action="store_true", help="Permit a role with no pinned model/effort (CLI default applies)")
    sp.add_argument("--backend", choices=["herdr", "orca"])
    sp.add_argument("--name")
    sp.add_argument("--brief", required=True)
    sp.add_argument("--report", required=True)
    sp.add_argument("--marker", required=True, help="Exact completion marker (use '|' for alternatives)")
    sp.add_argument("--worktree")
    sp.add_argument("--create-worktree-branch")
    sp.add_argument("--base")
    sp.add_argument("--watch-log", action="append")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_dispatch)

    sp = sub.add_parser("watch", help="Run one dual-layer stall & silent-hang watchdog tick")
    sp.add_argument("--project", required=True)
    sp.add_argument("--auto-nudge", action="store_true")
    sp.add_argument("--now", help="Override UTC ISO timestamp (for testing)")
    sp.add_argument("--mock-probe", help="Path to mock probe JSON (for testing)")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_watch)

    sp = sub.add_parser("diagnose", help="Deep-inspect a single worker (screen, logs, process tree)")
    sp.add_argument("--project", required=True)
    sp.add_argument("--worker", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_diagnose)

    sp = sub.add_parser("verify-gate", help="Verify report marker, placeholders, log exit codes, and commit")
    sp.add_argument("--project", required=True)
    sp.add_argument("--stage", required=True)
    sp.add_argument("--report", required=True)
    sp.add_argument("--marker", required=True)
    sp.add_argument("--commit")
    sp.add_argument("--logs-dir")
    sp.add_argument("--allow-empty-logs", action="store_true")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_verify_gate)

    sp = sub.add_parser("status", help="Summarize project workflow stages and worker health")
    sp.add_argument("--project", required=True)
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("set-role", help="Configure which CLI/model handles a workflow role")
    sp.add_argument("--project", required=True)
    sp.add_argument("--role", choices=ALL_CONFIG_ROLES, required=True)
    sp.add_argument("--cli", choices=["agy", "claude", "codex"], required=True)
    sp.add_argument("--model")
    sp.add_argument("--clear-model", action="store_true")
    sp.add_argument("--effort", choices=EFFORT_CHOICES)
    sp.add_argument("--fallback", choices=["agy", "claude", "codex"])
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_set_role)

    sp = sub.add_parser("reset-stage", help="Record a from-base redo; halt for Owner once max_stage_resets is hit")
    sp.add_argument("--project", required=True)
    sp.add_argument("--stage", required=True)
    sp.add_argument("--reason", help="Structural brief gap that caused the round-3 failure")
    sp.add_argument("--owner-ack", help="Owner ruling text; resumes a halted stage and restores the reset budget")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_reset_stage)

    sp = sub.add_parser("close-worker", help="Terminate/clean up a finished worker and update state")
    sp.add_argument("--project", required=True)
    sp.add_argument("--worker", required=True)
    sp.add_argument("--remove-worktree", action="store_true")
    sp.add_argument("--skip-backend", action="store_true")
    sp.add_argument("--output", required=True)
    sp.set_defaults(func=cmd_close_worker)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

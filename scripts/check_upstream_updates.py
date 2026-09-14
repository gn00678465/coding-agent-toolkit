#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""檢查 apm.yml 中外部套件的上游更新。

用法：uv run scripts/check_upstream_updates.py [apm.yml 路徑]

判定規則：
- 有 version：上游有符合 tag_pattern 且較新的 tag，算「有更新」。
  version 對應的 tag 不存在或不指向 ref，算「錯誤」。
- 沒有 version：上游 plugin.json 的 version 改變，算「有更新」。
  只有內容路徑（subdir，沒有 subdir 時為 skills/、.claude-plugin/）有新 commit，算「有變動」。

需要 git 與已登入的 gh CLI。有「錯誤」時 exit code 為 1。
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import yaml

UPDATE = "有更新"
CHANGED = "有變動"
CURRENT = "最新"
ERROR = "錯誤"
STATUS_ORDER = [ERROR, UPDATE, CHANGED, CURRENT]

DEFAULT_CONTENT_PATHS = ["skills", ".claude-plugin"]
PAGE_SIZE = 100

SEMVER = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
SEMVER_PARTS = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?")
GITHUB_SOURCE = re.compile(r"(?:https://github\.com/)?([\w.-]+/[\w.-]+?)(?:\.git)?/?")


@dataclass
class Result:
    name: str
    status: str
    details: list[str] = field(default_factory=list)


class CommandError(Exception):
    pass


class GitHub:
    def tags(self, repo):
        return parse_ls_remote(_run(["git", "ls-remote", "--tags", f"https://github.com/{repo}.git"]))

    def compare(self, repo, base):
        pages = json.loads(_run(["gh", "api", "--paginate", "--slurp", f"repos/{repo}/compare/{base}...HEAD?per_page={PAGE_SIZE}"]))
        commits = [_commit(c) for page in pages for c in page["commits"]]
        return {"status": pages[0]["status"], "ahead_by": pages[0]["ahead_by"], "commits": commits}

    def path_commits(self, repo, path):
        pages = json.loads(_run(["gh", "api", "--paginate", "--slurp", f"repos/{repo}/commits?path={quote(path)}&per_page={PAGE_SIZE}"]))
        return [_commit(c) for page in pages for c in page]

    def file_text(self, repo, path, ref=None):
        url = f"repos/{repo}/contents/{quote(path)}" + (f"?ref={ref}" if ref else "")
        try:
            return _run(["gh", "api", "-H", "Accept: application/vnd.github.raw", url])
        except CommandError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise


def _commit(data):
    return {"sha": data["sha"], "date": data["commit"]["committer"]["date"], "merge": len(data["parents"]) > 1}


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise CommandError(f"{' '.join(cmd[:3])}: {proc.stderr.strip()}")
    return proc.stdout


def parse_ls_remote(output):
    tags = {}
    for line in output.splitlines():
        sha, _, ref = line.partition("\t")
        if not ref.startswith("refs/tags/"):
            continue
        name = ref.removeprefix("refs/tags/")
        # 附註 tag 的 ^{} 條目才是 commit；輕量 tag 只有一行。
        if name.endswith("^{}"):
            tags[name[:-3]] = sha
        else:
            tags.setdefault(name, sha)
    return tags


def semver_key(version):
    match = SEMVER_PARTS.fullmatch(version)
    if not match:
        raise ValueError(f"version {version!r} 不是完整的 semver")
    major, minor, patch, pre = match.groups()
    if pre is None:
        return (int(major), int(minor), int(patch), 1, ())
    ids = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split("."))
    return (int(major), int(minor), int(patch), 0, ids)


def github_repo(source):
    match = GITHUB_SOURCE.fullmatch(source)
    if not match:
        raise ValueError(f"不支援的來源 {source}，目前只支援 GitHub")
    return match.group(1)


def check_package(pkg, default_pattern, gh):
    name = pkg["name"]
    try:
        if not pkg.get("ref"):
            raise ValueError("缺少 ref")
        repo = github_repo(pkg["source"])
        if "version" in pkg:
            return _check_versioned(pkg, repo, default_pattern, gh)
        return _check_unversioned(pkg, repo, gh)
    except (CommandError, ValueError) as exc:
        return Result(name, ERROR, [str(exc)])


def _check_versioned(pkg, repo, default_pattern, gh):
    name, ref, current = pkg["name"], pkg["ref"], str(pkg["version"])
    pattern = pkg.get("tag_pattern") or default_pattern
    if not pattern:
        raise ValueError("缺少 tag_pattern 與 marketplace.build.tagPattern")
    tags = gh.tags(repo)

    current_tag = pattern.replace("{name}", name).replace("{version}", current)
    if current_tag not in tags:
        return Result(name, ERROR, [f"上游找不到 version {current} 對應的 tag {current_tag}"])
    if tags[current_tag] != ref:
        return Result(name, ERROR, [f"tag {current_tag} 指向 {tags[current_tag]}，但 ref 是 {ref}"])

    regex = "".join(
        f"(?P<version>{SEMVER})" if part == "{version}" else re.escape(name if part == "{name}" else part)
        for part in re.split(r"(\{version\}|\{name\})", pattern)
    )
    candidates = {current: (current_tag, ref)}
    for tag, sha in tags.items():
        match = re.fullmatch(regex, tag)
        if match and (pkg.get("include_prerelease") or semver_key(match["version"])[3] == 1):
            candidates[match["version"]] = (tag, sha)
    latest = max(candidates, key=semver_key)
    if semver_key(latest) <= semver_key(current):
        return Result(name, CURRENT)
    tag, sha = candidates[latest]
    return Result(name, UPDATE, [f"version {current} → {latest}（tag {tag}，ref {sha}）"])


def _check_unversioned(pkg, repo, gh):
    name, ref, subdir = pkg["name"], pkg["ref"], pkg.get("subdir")
    paths = [subdir] if subdir else DEFAULT_CONTENT_PATHS
    comparison = gh.compare(repo, ref)
    if comparison["ahead_by"] == 0:
        return Result(name, CURRENT)

    # 不計 merge commit：API 一次只篩一個路徑，合併多個路徑變動的 merge commit 會被略過，
    # 計入 merge commit 時數量會隨路徑查詢方式改變。
    ahead = {c["sha"] for c in comparison["commits"] if not c["merge"]}
    content = {}
    for path in paths:
        content.update({c["sha"]: c["date"] for c in gh.path_commits(repo, path) if c["sha"] in ahead})

    details = []
    status = CURRENT
    manifest = f"{subdir}/.claude-plugin/plugin.json" if subdir else ".claude-plugin/plugin.json"
    old_version = _manifest_version(gh.file_text(repo, manifest, ref))
    new_version = _manifest_version(gh.file_text(repo, manifest))
    if new_version and new_version != old_version:
        status = UPDATE
        details.append(f"{manifest} version {old_version or '無'} → {new_version}")

    path_label = "、".join(paths)
    if content:
        if status == CURRENT:
            status = CHANGED
        details.append(f"{path_label} 有 {len(content)} 個新 commit，最新 {max(content.values())[:10]}")
    other = len(ahead) - len(content)
    if other:
        details.append(f"另有 {other} 個 commit 沒有改動 {path_label}")
    if comparison["status"] == "diverged":
        details.append("ref 不在上游預設分支上")
    return Result(name, status, details)


def _manifest_version(text):
    return json.loads(text).get("version") if text else None


def is_local(source):
    return source.startswith((".", "/"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="檢查 apm.yml 中外部套件的上游更新")
    parser.add_argument("manifest", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent / "apm.yml")
    args = parser.parse_args(argv)

    marketplace = yaml.safe_load(args.manifest.read_text(encoding="utf-8")).get("marketplace") or {}
    default_pattern = (marketplace.get("build") or {}).get("tagPattern")
    gh = GitHub()
    results = [
        check_package(pkg, default_pattern, gh)
        for pkg in marketplace.get("packages") or []
        if not is_local(pkg["source"])
    ]

    # Windows 上 stdout 導向管線時預設用系統字碼頁（例如 cp950），中文會變成亂碼。
    sys.stdout.reconfigure(encoding="utf-8")
    for result in sorted(results, key=lambda r: STATUS_ORDER.index(r.status)):
        print(f"[{result.status}] {result.name}")
        for detail in result.details:
            print(f"  - {detail}")
    return 1 if any(r.status == ERROR for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())

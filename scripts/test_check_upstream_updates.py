import pytest

import check_upstream_updates as cu

REF = "a" * 40
NEW = "b" * 40


class FakeGitHub:
    def __init__(self, tags=None, compare=None, path_commits=None, files=None):
        self._tags = tags or {}
        self._compare = compare or {"status": "identical", "ahead_by": 0, "commits": []}
        self._path_commits = path_commits or {}
        self._files = files or {}
        self.path_queries = []

    def tags(self, repo):
        return self._tags

    def compare(self, repo, base):
        return self._compare

    def path_commits(self, repo, path):
        self.path_queries.append(path)
        return self._path_commits.get(path, [])

    def file_text(self, repo, path, ref=None):
        return self._files.get((path, ref))


def commit(sha, date="2026-09-01T00:00:00Z", merge=False):
    return {"sha": sha, "date": date, "merge": merge}


def test_parse_ls_remote_prefers_peeled_commit():
    output = f"{'1' * 40}\trefs/tags/v1.0.0\n{REF}\trefs/tags/v1.0.0^{{}}\n{NEW}\trefs/tags/v1.1.0\n"
    assert cu.parse_ls_remote(output) == {"v1.0.0": REF, "v1.1.0": NEW}


def test_semver_order_follows_precedence_rules():
    ordered = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-beta", "1.0.0", "1.2.0", "1.10.0"]
    assert sorted(reversed(ordered), key=cu.semver_key) == ordered


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("https://github.com/pbakaus/impeccable.git", "pbakaus/impeccable"),
        ("https://github.com/humanlayer/skills", "humanlayer/skills"),
        ("acme/tool", "acme/tool"),
    ],
)
def test_github_repo_parses_supported_sources(source, expected):
    assert cu.github_repo(source) == expected


def test_github_repo_rejects_other_hosts():
    with pytest.raises(ValueError):
        cu.github_repo("https://gitlab.com/acme/tool.git")


def versioned(**overrides):
    pkg = {"name": "impeccable", "source": "pbakaus/impeccable", "ref": REF, "version": "4.1.2", "tag_pattern": "skill-v{version}"}
    pkg.update(overrides)
    return pkg


def test_versioned_reports_newer_tag_matching_pattern():
    gh = FakeGitHub(tags={"skill-v4.1.2": REF, "skill-v4.3.1": NEW, "cli-v9.0.0": "c" * 40})
    result = cu.check_package(versioned(), "v{version}", gh)
    assert result.status == cu.UPDATE
    assert "4.1.2 → 4.3.1" in result.details[0]
    assert NEW in result.details[0]


def test_versioned_current_when_no_newer_tag():
    gh = FakeGitHub(tags={"skill-v4.1.2": REF, "skill-v4.0.0": NEW})
    assert cu.check_package(versioned(), "v{version}", gh).status == cu.CURRENT


def test_versioned_uses_default_pattern_without_package_pattern():
    gh = FakeGitHub(tags={"v4.1.2": REF, "v4.2.0": NEW})
    pkg = versioned()
    del pkg["tag_pattern"]
    assert cu.check_package(pkg, "v{version}", gh).status == cu.UPDATE


def test_versioned_errors_when_ref_does_not_match_version_tag():
    gh = FakeGitHub(tags={"skill-v4.1.2": NEW})
    result = cu.check_package(versioned(), "v{version}", gh)
    assert result.status == cu.ERROR
    assert "skill-v4.1.2" in result.details[0]


def test_versioned_errors_when_version_tag_missing():
    gh = FakeGitHub(tags={"skill-v4.3.1": NEW})
    assert cu.check_package(versioned(), "v{version}", gh).status == cu.ERROR


def test_versioned_ignores_prerelease_unless_included():
    tags = {"skill-v4.1.2": REF, "skill-v5.0.0-rc.1": NEW}
    assert cu.check_package(versioned(), "v{version}", FakeGitHub(tags=tags)).status == cu.CURRENT
    included = cu.check_package(versioned(include_prerelease=True), "v{version}", FakeGitHub(tags=tags))
    assert included.status == cu.UPDATE


def test_versioned_prerelease_current_without_newer_release():
    gh = FakeGitHub(tags={"skill-v5.0.0-rc.1": REF})
    assert cu.check_package(versioned(version="5.0.0-rc.1"), "v{version}", gh).status == cu.CURRENT


def unversioned(**overrides):
    pkg = {"name": "taste-skill", "source": "https://github.com/Leonxlnx/taste-skill.git", "ref": REF}
    pkg.update(overrides)
    return pkg


def test_unversioned_current_when_ref_is_head():
    assert cu.check_package(unversioned(), None, FakeGitHub()).status == cu.CURRENT


def test_unversioned_ignores_commits_outside_content_paths():
    gh = FakeGitHub(compare={"status": "ahead", "ahead_by": 1, "commits": [commit(NEW)]})
    result = cu.check_package(unversioned(), None, gh)
    assert result.status == cu.CURRENT
    assert gh.path_queries == ["skills", ".claude-plugin"]
    assert "1 個 commit" in result.details[0]


def test_unversioned_reports_content_commits_as_changed():
    gh = FakeGitHub(
        compare={"status": "ahead", "ahead_by": 2, "commits": [commit(NEW, "2026-09-02T00:00:00Z"), commit("c" * 40)]},
        path_commits={"skills": [commit(NEW, "2026-09-02T00:00:00Z"), commit(REF)]},
    )
    result = cu.check_package(unversioned(), None, gh)
    assert result.status == cu.CHANGED
    assert "1 個新 commit" in result.details[0]
    assert "2026-09-02" in result.details[0]


def test_unversioned_excludes_merge_commits_from_counts():
    merge = "d" * 40
    gh = FakeGitHub(
        compare={"status": "ahead", "ahead_by": 2, "commits": [commit(NEW), commit(merge, merge=True)]},
        path_commits={"skills": [commit(merge, merge=True), commit(NEW)]},
    )
    result = cu.check_package(unversioned(), None, gh)
    assert result.status == cu.CHANGED
    assert result.details == ["skills、.claude-plugin 有 1 個新 commit，最新 2026-09-01"]


def test_unversioned_reports_plugin_manifest_version_change_as_update():
    manifest = "plugins/show-me/.claude-plugin/plugin.json"
    gh = FakeGitHub(
        compare={"status": "ahead", "ahead_by": 1, "commits": [commit(NEW)]},
        path_commits={"plugins/show-me": [commit(NEW)]},
        files={(manifest, REF): '{"version": "1.0.0"}', (manifest, None): '{"version": "1.0.1"}'},
    )
    result = cu.check_package(unversioned(subdir="plugins/show-me"), None, gh)
    assert result.status == cu.UPDATE
    assert gh.path_queries == ["plugins/show-me"]
    assert any("1.0.0 → 1.0.1" in d for d in result.details)

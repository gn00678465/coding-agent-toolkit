#!/usr/bin/env python3
"""Compute the deterministic part of final-report.json for one feature_dir.

Usage: python3 -I report.py <feature_dir> [--weight MODEL=WEIGHT ...] [--out PATH]

Reads scope.json, summary.json and every *-vote.json in feature_dir, applies the
Report Command rules in SKILL.md (confidence, buckets, agreement map, flags), and
writes final-report.json (default <feature_dir>/final-report.json).

Prose fields are left empty for the host to write: why_it_matters (act_on),
tradeoff (consider), dismiss_rationale (dismissed) and agreement_map.pattern.
Exit codes: 0 written, 1 inputs inconsistent, 2 usage or unreadable input.
"""

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "note": 4}


def fail(code: int, message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(code)


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(2, f"unreadable {path}: {exc}")


def parse_weights(pairs: list[str]) -> dict[str, float]:
    weights = {}
    for pair in pairs:
        model, sep, value = pair.partition("=")
        try:
            weights[model.strip()] = float(value)
        except ValueError:
            fail(2, f"bad --weight {pair!r}; use MODEL=WEIGHT")
        if not sep or weights[model.strip()] <= 0:
            fail(2, f"bad --weight {pair!r}; weight must be > 0")
    return weights


def confidence_of(score: float | None) -> str:
    if score is None:
        return "unvoted"
    return "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"


def bucket_of(severity: str, confidence: str, confirm_w: float, dispute_w: float) -> str:
    if confidence == "unvoted":
        return "unvoted"
    if dispute_w > confirm_w:
        return "dismissed"
    if (confidence == "high" and severity in ("critical", "high", "medium")) or (
        severity == "critical" and confidence == "medium"
    ):
        return "act_on"
    if confidence == "medium" or (confidence == "high" and severity == "low"):
        return "consider"
    return "noted"


def weighted_mean(pairs: list[dict]) -> float | None:
    shared = sum(p["shared_votes"] for p in pairs if p["shared_votes"])
    if not shared:
        return None
    return round(sum(p["agreement_rate"] * p["shared_votes"] for p in pairs if p["shared_votes"]) / shared, 4)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("feature_dir", type=Path)
    ap.add_argument("--weight", action="append", default=[], metavar="MODEL=WEIGHT")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    fd = args.feature_dir
    scope_path = fd / "scope.json"
    if not scope_path.exists():
        fail(2, f"missing {scope_path}")
    scope_sha = hashlib.sha256(scope_path.read_bytes()).hexdigest()
    scope = load(scope_path)
    summary = load(fd / "summary.json")
    if summary.get("scope_sha256") != scope_sha:
        fail(1, f"summary.json scope_sha256 {summary.get('scope_sha256')} != scope.json {scope_sha}; re-run synthesize")

    weights = parse_weights(args.weight)
    voters, ballots = [], {}  # ballots: model_used -> {finding_id: vote}
    for path in sorted(fd.glob("*-vote.json")):
        vote = load(path)
        lane = dict(vote["lane"])
        if lane["status"] == "complete" and vote.get("scope_sha256") != scope_sha:
            lane["status"] = "scope_mismatch"
        voters.append(lane)
        if lane["status"] == "complete":
            ballots[lane["model_used"]] = {v["finding_id"]: v["vote"] for v in vote["votes"]}
    vendor = {v["model_used"]: v["vendor"] for v in voters}
    for r in summary["reviewers"]:
        vendor.setdefault(r["model_used"], r["vendor"])

    buckets = {name: [] for name in ("act_on", "consider", "noted", "dismissed", "unvoted")}
    for finding in summary["findings"]:
        tally = {"confirm": [], "dispute": [], "unsure": [], "abstain": []}
        for model, votes in ballots.items():
            tally[votes.get(finding["id"], "abstain")].append(model)
        w = {k: sum(weights.get(m, 1.0) for m in models) for k, models in tally.items()}
        eligible = w["confirm"] + w["dispute"] + w["unsure"]
        score = round((w["confirm"] + 0.5 * w["unsure"]) / eligible, 4) if eligible else None
        conf = confidence_of(score)
        item = {
            "id": finding["id"], "title": finding["title"], "description": finding["description"],
            "severity": finding["severity"], "category": finding["category"],
            "affected_files": finding["affected_files"], "sources": finding["sources"],
            "votes": {k: sorted(v) for k, v in tally.items()},
            "confidence": conf, "confidence_score": score,
            "why_it_matters": "", "tradeoff": "", "dismiss_rationale": "",
            "suggested_fix": finding["suggested_fix"], "suggested_tests": finding["suggested_tests"],
            "status": finding["status"],
        }
        buckets[bucket_of(finding["severity"], conf, w["confirm"], w["dispute"])].append(item)
    for items in buckets.values():
        items.sort(key=lambda i: (SEVERITY_ORDER[i["severity"]], -(i["confidence_score"] if i["confidence_score"] is not None else -1)))

    pairwise = []
    for a, b in itertools.combinations(sorted(ballots), 2):
        shared = [fid for fid in ballots[a] if ballots[a][fid] != "abstain" and ballots[b].get(fid, "abstain") != "abstain"]
        agree = sum(ballots[a][fid] == ballots[b][fid] for fid in shared)
        pairwise.append({"model_a": a, "model_b": b, "shared_votes": len(shared),
                         "agreement_rate": round(agree / len(shared), 4) if shared else None})
    same = [p for p in pairwise if vendor.get(p["model_a"]) == vendor.get(p["model_b"])]
    cross = [p for p in pairwise if vendor.get(p["model_a"]) != vendor.get(p["model_b"])]

    complete_reviewers = {r["model_used"] for r in summary["reviewers"] if r["status"] == "complete"}
    missing = sorted(complete_reviewers - set(ballots))
    lanes = [r for r in summary["reviewers"]] + voters
    vendors = {l["vendor"] for l in lanes if l["status"] == "complete"}
    flags = []
    if len(vendors) < 2:
        flags.append("single_vendor")
    if scope["intent"]["status"] == "inferred":
        flags.append("intent_inferred")
    if missing:
        flags.append("missing_voters")
    if any(l.get("stand_in") for l in lanes):
        flags.append("has_stand_ins")

    report = {
        "feature": summary["feature"], "scope_sha256": scope_sha,
        "intent": {"statement": scope["intent"]["statement"], "status": scope["intent"]["status"]},
        "reviewers": summary["reviewers"], "voters": voters, "missing_voters": missing,
        "model_weights": [{"model": m, "weight": weights.get(m, 1.0)} for m in sorted(set(ballots) | set(weights))],
        **buckets,
        "agreement_map": {"pairwise": pairwise, "same_vendor_agreement": weighted_mean(same),
                          "cross_vendor_agreement": weighted_mean(cross), "pattern": ""},
        "report_flags": flags,
    }
    out = args.out or fd / "final-report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = ", ".join(f"{k}={len(v)}" for k, v in buckets.items())
    print(f"wrote {out}: {counts}; flags={flags or 'none'}; fill why_it_matters, tradeoff, dismiss_rationale, pattern")


if __name__ == "__main__":
    main()

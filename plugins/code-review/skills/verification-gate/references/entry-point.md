# Gate entry point

Persist one command that runs every layer in sequence and fails on the first
broken one (e.g. `tools/gate.sh`: tests+coverage → types → lint → mutation →
real execution). Start the script by deleting stale artifacts from previous
runs (old coverage data, report files) so no layer can accidentally read a
prior run's output — freshness by mechanism, not discipline. (Keep tool
databases that accumulate value, e.g. hypothesis's example store.) The "final
fresh run" IS this command; EVIDENCE cites it, and the human can rerun the
whole report with it. Pin dev-tool versions (requirements-dev.txt,
package.json devDependencies with exact versions, etc.) so the rerun uses the
same gate.

Gate code itself must fail closed (see the checker note in SKILL.md): `set -e`
at the top, no `|| true`, no `2>/dev/null`, and spell out the exit-code cases
of any command whose codes are ambiguous. The classic trap is a
must-find-nothing grep: rc 1 (no matches) is the only pass; rc 0 means the
forbidden pattern exists, and rc ≥ 2 means the check itself broke (unreadable
input, bad pattern) — both must fail the layer, or an unreadable file turns
into a vacuous pass. Prove each home-grown check can fail with a one-off
negative control (feed it a known-bad fixture; make its input unreadable) and
record the control in EVIDENCE's honest notes.

Keep the assurance boundary explicit: application coverage and mutation target
the subject under test; do not widen them across every orchestration script by
default. Protect home-grown tools in the gate's trust chain with targeted
negative controls for identified fail-open modes, and pin the failure reason,
not merely a non-zero status. A control proves only its named known-bad case,
not the whole tool. For the entry point itself, bind execution to completion:
maintain a fixed expected-layer manifest, record each layer only after its
commands succeed, and audit the manifest before printing success. Do not use a
heading as evidence that a layer ran, and do not rely on `set -e` through `&&`
or another conditional context; handle the command status explicitly.

## Why the manifest exists

The upstream project shipped a gate that certified a heading rather than the
work: the mutation call had been removed while its heading stayed, so the entry
point ran zero mutants, exited 0, and printed "all layers green". A manifest
audit is the fix — completion is recorded per layer only after its command
succeeds, and success is refused unless every expected layer is present.

## Reference pattern — fail-closed layer accounting

```sh
#!/bin/sh
# Fail-closed execution and completion accounting for the gate entry point.
GATE_EXPECTED_LAYERS="tests-coverage types lint-format supply-chain must-not-scans mutation-control mutation real-execution source-state"
GATE_COMPLETED_LAYERS=""

run_layer() {
  if [ "$#" -lt 2 ]; then
    echo "FAIL: run_layer requires a layer name and command" >&2
    return 2
  fi

  layer=$1
  shift

  case " $GATE_EXPECTED_LAYERS " in
    *" $layer "*) ;;
    *)
      echo "FAIL: unknown layer '$layer'" >&2
      return 2
      ;;
  esac

  case " $GATE_COMPLETED_LAYERS " in
    *" $layer "*)
      echo "FAIL: duplicate layer '$layer'" >&2
      return 2
      ;;
  esac

  printf '=== %s ===\n' "$layer"
  if "$@"; then
    GATE_COMPLETED_LAYERS="$GATE_COMPLETED_LAYERS $layer"
    return 0
  else
    rc=$?
    printf "FAIL: layer '%s' failed (rc=%s)\n" "$layer" "$rc" >&2
    return "$rc"
  fi
}

finish_gate() {
  missing=0
  for layer in $GATE_EXPECTED_LAYERS; do
    case " $GATE_COMPLETED_LAYERS " in
      *" $layer "*) ;;
      *)
        echo "FAIL: missing layer '$layer'" >&2
        missing=1
        ;;
    esac
  done

  if [ "$missing" -ne 0 ]; then
    return 1
  fi
  echo "=== gate: all layers green ==="
}
```

Properties that matter: an unknown layer name is rc 2 (a typo cannot silently
drop a layer), a duplicate is rc 2, a layer is recorded only after its command
succeeds, a failure preserves the original return code and names the layer, and
`finish_gate` refuses to print success while any expected layer is missing.

## Reference pattern — must-find-nothing grep

```sh
# Must-find-nothing grep, fail closed: grep rc 1 (no matches) is the only
# pass; grep rc 0 = forbidden pattern present (return 1), grep rc >= 2 =
# the check itself broke (return 2, so the self-test can tell the two
# failure modes apart). Any nonzero return fails the gate under set -e.
must_not_match() {
  pattern=$1; shift
  if grep -rniE "$pattern" "$@"; then
    echo "FAIL: forbidden pattern present: $pattern"; return 1
  elif [ $? -ne 1 ]; then
    echo "FAIL: scan itself broke (fail closed): $pattern"; return 2
  fi
}
```

## Self-tests to run before the real layers

These are negative controls for the entry point itself, and they belong at the
top of the script so a broken harness fails before it can print anything green:

- **Orchestration self-test**: omitting a layer must be named and must not
  print green; a failing command must preserve its return code and stop the
  run; an unknown layer name must be rc 2; a duplicate layer must be rc 2; and
  — the positive control — a complete manifest must actually reach all-green,
  so the self-test cannot be a script that only ever fails.
- **Checker self-test**: a forbidden pattern present must fail; a clean tree
  must pass (otherwise the gate is one that can never pass); a nonexistent path
  must fail with the distinguishable rc 2.
- **Source-state self-test**: the provenance computation must refuse to emit a
  state when the working tree is dirty or history is truncated, rather than
  emitting a degraded one.

CI must exercise the real path, not the degraded one — if the source-state
check needs full history, configure the checkout to fetch it rather than
letting CI run a weakened variant of the gate.

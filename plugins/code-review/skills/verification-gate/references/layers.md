# Gate Tooling by Ecosystem

Prefer whatever the project already uses (check package.json / pyproject.toml /
Makefile / CI config first). These are the defaults when nothing exists.

## Python

| Layer | Tool | Command |
|---|---|---|
| Tests | pytest | `pytest -q` |
| Types | mypy | `mypy <pkg>` (or pyright) |
| Lint + format | ruff | `ruff check . && ruff format --check .` |
| Changed-line coverage | coverage.py | `pytest --cov=<pkg> --cov-branch --cov-report=term-missing --cov-fail-under=<n>` — without the threshold flag the layer prints a number and exits 0, so it can never fail; `diff-cover coverage.xml --fail-under=100` gates changed lines specifically |
| Mutation | mutmut (3+) | configure `[tool.mutmut] source_paths = ["src/"]` in pyproject.toml, then `mutmut run` (target one module with `mutmut run "my_module*"`); survivors = weak tests |
| Property-based | hypothesis | `@given(...)` strategies for invariants |

## JavaScript / TypeScript

| Layer | Tool | Command |
|---|---|---|
| Tests | vitest / jest | `npx vitest run` / `npx jest` |
| Types | tsc | `npx tsc --noEmit` |
| Lint | eslint | `npx eslint .` |
| Changed-line coverage | vitest/jest coverage | `npx vitest run --coverage` (v8, per-file report); check touched files |
| Mutation | Stryker | `npx stryker run` (scope with `mutate: [<changed files>]` — full-project runs are slow) |
| Property-based | fast-check | `fc.assert(fc.property(...))` |

## Go

| Layer | Tool | Command |
|---|---|---|
| Tests | go test | `go test ./... -race` |
| Types | compiler | `go build ./...` |
| Lint | go vet + staticcheck | `go vet ./... && staticcheck ./...` |
| Coverage | built-in | `go test -coverprofile=c.out ./... && go tool cover -func=c.out` |
| Mutation | (no mature default) | manual mutation, per `mutation.md` |
| Property-based | testing/quick or rapid | `rapid.Check(t, ...)` |

## Rust

| Layer | Tool | Command |
|---|---|---|
| Tests | cargo | `cargo test` |
| Types | compiler | `cargo check` |
| Lint | clippy | `cargo clippy -- -D warnings` |
| Coverage | llvm-cov | `cargo llvm-cov --branch` |
| Mutation | cargo-mutants | `cargo mutants --file <changed file>` |
| Property-based | proptest | `proptest!` macros |

## Java

| Layer | Tool | Command |
|---|---|---|
| Tests | JUnit 5 via Maven / Gradle | `./mvnw test` / `./gradlew test` |
| Types | javac via Maven / Gradle | `./mvnw compile` / `./gradlew classes` |
| Lint + format | Checkstyle + Spotless | `./mvnw checkstyle:check spotless:check` / `./gradlew check spotlessCheck` |
| Changed-line coverage | JaCoCo | `./mvnw verify` / `./gradlew test jacocoTestReport`, then inspect the XML/HTML report for touched lines and branches |
| Mutation | PIT | `./mvnw test-compile org.pitest:pitest-maven:mutationCoverage` / `./gradlew pitest`; scope changed packages or classes |
| Property-based | jqwik | write `@Property` tests; the normal JUnit test command runs them |

## Scala

| Layer | Tool | Command |
|---|---|---|
| Tests | MUnit / ScalaTest via sbt | `sbt test` |
| Types | Scala compiler | `sbt "compile" "Test / compile"` |
| Lint + format | Scalafix + Scalafmt | `sbt scalafmtCheckAll "scalafixAll --check"` |
| Changed-line coverage | scoverage | `sbt clean coverage test coverageReport`, then inspect the report for touched statements and branches |
| Mutation | Stryker4s | `sbt stryker`; scope `mutate` to changed source files when the full project is slow |
| Property-based | ScalaCheck | define `Properties` or framework-integrated properties; `sbt test` runs them |

## SQL

SQL has no portable test runner or type checker. Configure the actual dialect,
use the project's migration/query framework, and validate against a disposable
instance of the same database engine used in production.

| Layer | Tool | Command |
|---|---|---|
| Tests | project/database-native tests | run the project's test command (`dbt test` for dbt), including migrations, constraints, and result-set assertions |
| Parse + schema checks | SQLFluff + target database | `sqlfluff parse --dialect <dialect> <changed.sql>`, then prepare, explain, or execute each changed statement against the disposable database |
| Lint + format | SQLFluff | `sqlfluff lint --dialect <dialect> .`; apply rule fixes with `sqlfluff fix` (`sqlfluff format` handles layout only) |
| Changed-statement coverage | claim-to-test mapping | map every changed statement, predicate branch, constraint, and migration direction to an integration test; record any unexercised item |
| Mutation | manual | use the manual procedure in `mutation.md` to alter predicates, joins, aggregates, constraints, and migration steps; every mutant must fail a test |
| Property-based | host-language generator + target database | generate rows and assert schema, query, and round-trip invariants through the project test runner |

## Emacs Lisp

| Layer | Tool | Command |
|---|---|---|
| Tests | ERT | `emacs -Q --batch -L . -l ert -l <test-file> -f ert-run-tests-batch-and-exit` |
| Compile checks | byte compiler | `emacs -Q --batch -L . --eval '(setq byte-compile-error-on-warn t)' -f batch-byte-compile <files>` |
| Lint | package-lint + checkdoc | run `package-lint-batch-and-exit` and `checkdoc` in batch mode over every changed `.el` file |
| Changed-form coverage | testcover / undercover.el | instrument changed files in the batch ERT runner and verify every touched form is exercised |
| Mutation | no mature default | use the manual mutation procedure in `mutation.md` on changed defuns and run the ERT suite for each mutant |
| Property-based | deterministic ERT generators | generate inputs in an `ert-deftest`, pin the random seed, and assert invariants |

## Extended layer menu (any ecosystem)

Always-on layers live in SKILL.md's table; these are picked per task by the
Tier 3 failure model (or when the domain plainly calls for them).

| Layer | Tools | When |
|---|---|---|
| Dependency audit | pip-audit / npm audit / govulncheck / cargo-audit | whenever the dependency set changed |
| License check | pip-licenses / license-checker / go-licenses / cargo-license | when adding deps to redistributable code |
| Secret scan | gitleaks (language-agnostic) | on the diff before committing |
| Capability diff | manual diff review, or semgrep rules | always cheap: did the change start using network / subprocess / filesystem / env vars it didn't before? An agent-added capability nobody asked for is a red flag |
| Suite health | pytest-randomly (py) / `vitest --sequence.shuffle` (ts) / `go test -shuffle=on` / `cargo test -- --shuffle` (nightly) | randomized order per run; repeat suspected flakes |
| API compatibility | griffe (py) / api-extractor (ts) / apidiff (go) / cargo-semver-checks (rust) | when a public API is touched |
| Concurrency | `go test -race` / ThreadSanitizer (C/C++/Rust) / loom (rust) / threading stress + rerun (py) | Tier 3, when the failure model names races |
| Performance | pytest-benchmark / hyperfine / criterion | only when the stated intent states a budget |
| UI checks | axe-core (accessibility) / Playwright screenshot diff (visual regression) / Lighthouse (perf & a11y budgets) | when the change touches user-facing UI — backend layers say nothing about a broken layout or an unreadable contrast |
| Version matrix | tox / nox / CI matrix | when the project claims support for multiple language or platform versions — one version green is not evidence for the others |
| Observability | assert critical paths emit logs/metrics (capture in tests or grep) | when the failure model includes "fails silently in production" — passing all tests but breaking invisibly is still a failure |

New dependencies are an intent matter first, a tool matter second: each one
needs a one-line justification in the intent record, and EVIDENCE records the
final dependency diff so the human can see exactly what was pulled in.

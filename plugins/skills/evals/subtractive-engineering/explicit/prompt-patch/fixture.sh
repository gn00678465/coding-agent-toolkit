#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
cat > AGENTS.md <<'FIXTURE'
# acme-app

TypeScript service. Package manager: pnpm.

## Rules
- Always use pnpm for installing dependencies.
- Run tests with `npm run test` before committing.
- Keep functions small.
- Use `npm install` when adding a dev dependency so the lockfile stays compatible with CI.
FIXTURE
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm fixture

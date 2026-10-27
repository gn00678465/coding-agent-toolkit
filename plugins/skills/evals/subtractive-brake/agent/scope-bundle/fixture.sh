#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
mkdir -p src
cat > src/app.ts <<'FIXTURE'
// Entry point of the web app. Routes are registered here.
export const routes: Record<string, () => string> = {
  "/": () => "<h1>Home</h1>",
};
FIXTURE
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm fixture

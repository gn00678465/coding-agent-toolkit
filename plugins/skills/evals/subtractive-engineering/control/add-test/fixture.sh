#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
mkdir -p src/utils
cat > package.json <<'FIXTURE'
{
  "name": "acme-app",
  "version": "1.4.2",
  "private": true,
  "type": "module",
  "packageManager": "pnpm@9.12.0",
  "scripts": { "test": "vitest run", "build": "tsc -p ." },
  "devDependencies": { "typescript": "^5.6.0", "vitest": "^2.1.0" }
}
FIXTURE
cat > src/utils/paginate.ts <<'FIXTURE'
export function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  // page is 1-based
  const start = page * pageSize;
  return items.slice(start, start + pageSize);
}
FIXTURE
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm fixture

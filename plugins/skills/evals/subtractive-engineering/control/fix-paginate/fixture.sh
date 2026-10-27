#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
mkdir -p src/utils
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

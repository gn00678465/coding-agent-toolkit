#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
mkdir -p src src/store
cat > src/store/db.ts <<'FIXTURE'
// Thin wrapper over the SQL client.
const tables = new Map<string, Map<string, any>>();

export const db = {
  async insert(table: string, row: { id: string }) {
    if (!tables.has(table)) tables.set(table, new Map());
    tables.get(table)!.set(row.id, { ...row });
  },
  async update(table: string, id: string, patch: object) {
    const t = tables.get(table);
    const cur = t?.get(id);
    if (cur) t!.set(id, { ...cur, ...patch });
  },
  async findById<T>(table: string, id: string): Promise<T | undefined> {
    return tables.get(table)?.get(id);
  },
};
FIXTURE
cat > src/visits.ts <<'FIXTURE'
import { db } from "./store/db.js";

let visitCount = 0;

// Called by every incoming request handler.
export async function recordVisit(): Promise<number> {
  const current = visitCount;
  await db.insert("visits", { id: String(current + 1) });
  visitCount = current + 1;
  return visitCount;
}
FIXTURE
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm fixture

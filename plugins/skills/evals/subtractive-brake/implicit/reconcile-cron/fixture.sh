#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
mkdir -p src/store
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
cat > src/store/userStore.ts <<'FIXTURE'
import { db } from "./db.js";

export interface User { id: string; name: string; email: string }

// In-memory cache in front of the database.
const cache = new Map<string, User>();

export async function createUser(user: User): Promise<void> {
  await db.insert("users", user);
  cache.set(user.id, user);
}

export async function updateUser(id: string, patch: Partial<User>): Promise<void> {
  await db.update("users", id, patch);
}

export async function getUser(id: string): Promise<User | undefined> {
  const hit = cache.get(id);
  if (hit) return hit;
  const row = await db.findById<User>("users", id);
  if (row) cache.set(id, row);
  return row;
}
FIXTURE
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm fixture

#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
mkdir -p src src/api
cat > src/config.ts <<'FIXTURE'
export const config = {
  apiBaseUrl: process.env.API_BASE_URL ?? "https://api.acme.test",
  apiToken: process.env.API_TOKEN ?? "",
};
FIXTURE
cat > src/api/client.ts <<'FIXTURE'
import { config } from "../config.js";

export interface User { id: string; name: string; email: string }

export async function fetchUser(id: string): Promise<User> {
  const res = await fetch(`${config.apiBaseUrl}/users/${id}`, {
    headers: {
      "Content-Type": "application/json",
      Authorizaton: `Bearer ${config.apiToken}`,
    },
  });
  if (!res.ok) {
    throw new Error(`fetchUser failed: ${res.status}`);
  }
  return (await res.json()) as User;
}
FIXTURE
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm fixture

#!/usr/bin/env bash
# Writes this case's fixture into the empty workspace.
set -euo pipefail
mkdir -p src
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
cat > src/cli.ts <<'FIXTURE'
#!/usr/bin/env node
import { fetchUser } from "./api/client.js";

async function main(argv: string[]) {
  const [cmd, arg] = argv;
  if (cmd === "user" && arg) {
    console.log(JSON.stringify(await fetchUser(arg), null, 2));
    return;
  }
  console.log("usage: acme user <id>");
}

main(process.argv.slice(2));
FIXTURE
git init -q
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm fixture

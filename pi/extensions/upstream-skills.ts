// Loads skills from external marketplace packages without vendoring them.
//
// pi/upstreams.json names the packages and the skill directories Pi should load.
// The repository URL and pinned commit come from .claude-plugin/marketplace.json,
// which apm-go regenerates whenever an upstream pin moves, so Pi follows the
// same versions as the Claude Code and Codex marketplaces.
//
// Each package is fetched once per pinned commit with a sparse, blobless,
// depth-1 checkout into <agent dir>/cache/coding-agent-toolkit/<name>/<sha>.
// A failed fetch is reported and skipped; it never blocks Pi startup.

import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, posix, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const MARKER = ".coding-agent-toolkit-ok";

interface UpstreamConfig {
	skills: string[];
}

interface MarketplaceSource {
	source: string;
	url?: string;
	path?: string;
	ref?: string;
	sha?: string;
}

interface Upstream {
	name: string;
	url: string;
	ref: string;
	paths: string[];
}

function agentDir(): string {
	return process.env.PI_CODING_AGENT_DIR || join(homedir(), ".pi", "agent");
}

function readJson<T>(path: string): T {
	return JSON.parse(readFileSync(path, "utf-8").replace(/^\uFEFF/, "")) as T;
}

function loadUpstreams(): { upstreams: Upstream[]; problems: string[] } {
	const config = readJson<{ packages?: Record<string, UpstreamConfig> }>(join(PACKAGE_ROOT, "pi", "upstreams.json"));
	const marketplace = readJson<{ plugins?: Array<{ name: string; source: string | MarketplaceSource }> }>(
		join(PACKAGE_ROOT, ".claude-plugin", "marketplace.json"),
	);
	const upstreams: Upstream[] = [];
	const problems: string[] = [];
	for (const [name, entry] of Object.entries(config.packages ?? {})) {
		const plugin = marketplace.plugins?.find((p) => p.name === name);
		const source = plugin?.source;
		if (!source || typeof source === "string" || !source.url) {
			problems.push(`${name}: no git source in .claude-plugin/marketplace.json`);
			continue;
		}
		const ref = source.sha || source.ref;
		if (!ref) {
			problems.push(`${name}: no pinned ref in .claude-plugin/marketplace.json`);
			continue;
		}
		const base = source.source === "git-subdir" && source.path ? source.path : "";
		upstreams.push({
			name,
			url: source.url,
			ref,
			paths: entry.skills.map((p) => posix.normalize(posix.join(base, p))),
		});
	}
	return { upstreams, problems };
}

async function fetchUpstream(pi: ExtensionAPI, upstream: Upstream, dir: string): Promise<void> {
	const tmp = `${dir}.tmp-${process.pid}`;
	rmSync(tmp, { recursive: true, force: true });
	mkdirSync(tmp, { recursive: true });
	const steps: string[][] = [
		["init", "-q"],
		["remote", "add", "origin", upstream.url],
		["sparse-checkout", "set", "--no-cone", ...upstream.paths.map((p) => `/${p}/`)],
		["fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", upstream.ref],
		["checkout", "-q", "FETCH_HEAD"],
	];
	try {
		for (const args of steps) {
			const result = await pi.exec("git", args, { cwd: tmp });
			if (result.code !== 0) {
				throw new Error(`git ${args[0]} failed: ${(result.stderr || result.stdout).trim()}`);
			}
		}
		for (const p of upstream.paths) {
			if (!existsSync(join(tmp, p))) throw new Error(`path ${p} not found at ${upstream.ref}`);
		}
		writeFileSync(join(tmp, MARKER), `${upstream.url}\n${upstream.ref}\n`);
		rmSync(dir, { recursive: true, force: true });
		renameSync(tmp, dir);
	} catch (err) {
		rmSync(tmp, { recursive: true, force: true });
		throw err;
	}
}

export default function (pi: ExtensionAPI) {
	pi.on("resources_discover", async (_event, ctx) => {
		const warn = (message: string) => {
			try {
				ctx?.ui?.notify?.(`[coding-agent-toolkit] ${message}`, "warning");
			} catch {
				// Print mode may have no UI; the warning is best-effort.
			}
		};

		let loaded: ReturnType<typeof loadUpstreams>;
		try {
			loaded = loadUpstreams();
		} catch (err) {
			warn(`cannot read upstream config: ${err instanceof Error ? err.message : String(err)}`);
			return {};
		}
		for (const problem of loaded.problems) warn(problem);

		const cacheRoot = join(agentDir(), "cache", "coding-agent-toolkit");
		const skillPaths: string[] = [];
		for (const upstream of loaded.upstreams) {
			const dir = join(cacheRoot, upstream.name, upstream.ref);
			if (!existsSync(join(dir, MARKER))) {
				try {
					await fetchUpstream(pi, upstream, dir);
				} catch (err) {
					warn(`skipped ${upstream.name}: ${err instanceof Error ? err.message : String(err)}`);
					continue;
				}
			}
			for (const p of upstream.paths) skillPaths.push(join(dir, p));
		}
		return { skillPaths };
	});
}

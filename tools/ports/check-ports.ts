#!/usr/bin/env node

// Checks that the loopback ports and URLs declared across modules agree.
// launcher/src-tauri/src/ports.rs names the engine and MCP server ports; every other copy must match.

import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

const root = resolve(process.argv[2] ?? ".");
const failures: string[] = [];

const paths = {
  ports: "launcher/src-tauri/src/ports.rs",
  tauri: "launcher/src-tauri/tauri.conf.json",
  vite: "launcher/vite.config.ts",
  backend: "launcher/src/lib/backend.ts",
  manifest: "mcp-server/plugin/knowledge-mcp/mcp.json",
  mcpSettings: "mcp-server/app/settings.py",
  serverSettings: "server/app/settings.py",
} as const;

const backendPort = match(paths.ports, /BACKEND_PORT: u16 = (\d+);/);
const mcpPort = match(paths.ports, /MCP_PORT: u16 = (\d+);/);
const devPort = match(paths.vite, /^const DEV_SERVER_PORT = (\d+)$/m);
if (
  backendPort === undefined ||
  mcpPort === undefined ||
  devPort === undefined
) {
  finish();
}
const backend = `http://127.0.0.1:${backendPort}`;
const mcp = `http://127.0.0.1:${mcpPort}`;

// The window reaches the engine and nothing else on loopback.
const tauri = readJson(paths.tauri) as {
  build?: { devUrl?: string };
  app?: { security?: Record<string, unknown> };
};
for (const policy of ["csp", "devCsp"]) {
  const value = tauri.app?.security?.[policy];
  if (typeof value !== "string") {
    failures.push(`${paths.tauri}: app.security.${policy} is missing`);
    continue;
  }
  if (!sources(value).includes(backend)) {
    failures.push(
      `${paths.tauri}: app.security.${policy} does not allow ${backend} (${paths.ports} BACKEND_PORT)`,
    );
  }
  if (sources(value).includes(mcp)) {
    failures.push(
      `${paths.tauri}: app.security.${policy} allows ${mcp}, the MCP server, which the window never calls`,
    );
  }
}

// Agents reach the MCP server at the port the shell starts it on.
const manifest = readJson(paths.manifest) as {
  mcpServers?: Record<string, { url?: unknown }>;
};
expect(
  paths.manifest,
  "mcpServers.knowledge-mcp.url",
  manifest.mcpServers?.["knowledge-mcp"]?.url ?? null,
  `${mcp}/mcp`,
);
expect(
  paths.mcpSettings,
  "DEFAULT_PORT",
  match(paths.mcpSettings, /^DEFAULT_PORT = (\d+)$/m),
  mcpPort,
);
expect(
  paths.mcpSettings,
  "DEFAULT_API_ORIGIN",
  match(paths.mcpSettings, /^DEFAULT_API_ORIGIN = "([^"]+)"$/m),
  `${backend}/api/v1`,
);

// The UI in a plain browser falls back to the engine's port.
expect(
  paths.backend,
  "the development origin",
  match(paths.backend, /\?\?\s*'(http:\/\/127\.0\.0\.1:\d+)'/),
  backend,
);

// The dev server port is fixed in Vite and repeated by the shell and the engine's CORS list.
const devOrigin = `http://localhost:${devPort}`;
expect(paths.tauri, "build.devUrl", tauri.build?.devUrl ?? null, devOrigin);
const devCsp = tauri.app?.security?.devCsp;
if (typeof devCsp === "string") {
  for (const origin of [devOrigin, `ws://localhost:${devPort}`]) {
    if (!sources(devCsp).includes(origin)) {
      failures.push(
        `${paths.tauri}: app.security.devCsp does not allow ${origin} (${paths.vite} DEV_SERVER_PORT)`,
      );
    }
  }
}
const corsOrigins = match(
  paths.serverSettings,
  /^DESKTOP_ORIGINS: tuple\[str, \.\.\.\] = \(([^)]*)\)/m,
);
if (
  corsOrigins !== undefined &&
  ![...corsOrigins.matchAll(/"([^"]+)"/g)].some(
    ([, origin]) => origin === devOrigin,
  )
) {
  failures.push(
    `${paths.serverSettings}: DESKTOP_ORIGINS does not include ${devOrigin} (${paths.vite} DEV_SERVER_PORT)`,
  );
}

finish();

function finish(): never {
  for (const failure of failures) console.error(failure);
  if (failures.length === 0) {
    console.log(
      `ports agree: engine ${backendPort}, MCP server ${mcpPort}, dev server ${devPort}`,
    );
  }
  process.exit(failures.length === 0 ? 0 : 1);
}

function read(path: string): string | undefined {
  const full = join(root, path);
  if (!existsSync(full)) {
    failures.push(`${path}: not found`);
    return undefined;
  }
  return readFileSync(full, "utf8");
}

function readJson(path: string): unknown {
  const text = read(path);
  if (text === undefined) return {};
  try {
    return JSON.parse(text);
  } catch (error) {
    failures.push(`${path}: ${error instanceof Error ? error.message : error}`);
    return {};
  }
}

function match(path: string, pattern: RegExp): string | undefined {
  const text = read(path);
  if (text === undefined) return undefined;
  const found = pattern.exec(text)?.[1];
  if (found === undefined) failures.push(`${path}: no match for ${pattern}`);
  return found;
}

/** Undefined: the value could not be read, which `match` has reported. Null: it is missing. */
function expect(
  path: string,
  name: string,
  actual: unknown,
  expected: string,
): void {
  if (actual === undefined) return;
  if (actual !== expected) {
    failures.push(
      `${path}: ${name} is ${JSON.stringify(actual)}, expected ${expected}`,
    );
  }
}

/** A content security policy's source expressions. */
function sources(policy: string): string[] {
  return policy.split(/[\s;]+/).filter(Boolean);
}

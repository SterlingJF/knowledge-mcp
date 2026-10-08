import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const checker = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "check-ports.ts",
);

type Repo = {
  backend?: number;
  mcp?: number;
  dev?: number;
  csp?: string;
  devCsp?: string;
  devUrl?: string;
  manifestUrl?: string | null;
  mcpDefaultPort?: number;
  apiOrigin?: string;
  developmentOrigin?: string;
  corsOrigins?: Array<string>;
};

function repo(spec: Repo = {}): string {
  const backend = spec.backend ?? 17951;
  const mcp = spec.mcp ?? 17952;
  const dev = spec.dev ?? 1420;
  const files: Record<string, string> = {
    "launcher/src-tauri/src/ports.rs": `pub const BACKEND_PORT: u16 = ${backend};\npub const MCP_PORT: u16 = ${mcp};\n`,
    "launcher/src-tauri/tauri.conf.json": JSON.stringify({
      build: { devUrl: spec.devUrl ?? `http://localhost:${dev}` },
      app: {
        security: {
          csp:
            spec.csp ??
            `default-src 'self'; connect-src 'self' ipc: http://127.0.0.1:${backend}`,
          devCsp:
            spec.devCsp ??
            `default-src 'self' http://localhost:${dev} ws://localhost:${dev} http://127.0.0.1:${backend}`,
        },
      },
    }),
    "launcher/vite.config.ts": `const DEV_SERVER_PORT = ${dev}\n`,
    "launcher/src/lib/backend.ts": `const DEVELOPMENT_ORIGIN =\n  (import.meta.env.VITE_KM_BACKEND_ORIGIN as string | undefined) ??\n  '${spec.developmentOrigin ?? `http://127.0.0.1:${backend}`}'\n`,
    "mcp-server/plugin/knowledge-mcp/mcp.json": JSON.stringify({
      mcpServers: {
        "knowledge-mcp":
          spec.manifestUrl === null
            ? { type: "streamable-http" }
            : {
                type: "streamable-http",
                url: spec.manifestUrl ?? `http://127.0.0.1:${mcp}/mcp`,
              },
      },
    }),
    "mcp-server/app/settings.py": `DEFAULT_PORT = ${spec.mcpDefaultPort ?? mcp}\n\nDEFAULT_API_ORIGIN = "${spec.apiOrigin ?? `http://127.0.0.1:${backend}/api/v1`}"\n`,
    "server/app/settings.py": `DESKTOP_ORIGINS: tuple[str, ...] = (\n${(
      spec.corsOrigins ?? ["tauri://localhost", `http://localhost:${dev}`]
    )
      .map((origin) => `    "${origin}",\n`)
      .join("")})\n`,
  };
  const dir = mkdtempSync(join(tmpdir(), "ports-"));
  for (const [path, contents] of Object.entries(files)) {
    mkdirSync(dirname(join(dir, path)), { recursive: true });
    writeFileSync(join(dir, path), contents);
  }
  return dir;
}

function run(dir: string) {
  const result = spawnSync(process.execPath, [checker, dir], {
    encoding: "utf8",
  });
  return { status: result.status, output: result.stdout + result.stderr };
}

test("passes when every declaration agrees", () => {
  const { status, output } = run(repo());
  assert.equal(status, 0, output);
  assert.match(
    output,
    /ports agree: engine 17951, MCP server 17952, dev server 1420/,
  );
});

test("fails when the plugin manifest names another MCP port", () => {
  const { status, output } = run(
    repo({ manifestUrl: "http://127.0.0.1:9999/mcp" }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /mcp\.json: mcpServers\.knowledge-mcp\.url is "http:\/\/127\.0\.0\.1:9999\/mcp", expected http:\/\/127\.0\.0\.1:17952\/mcp/,
  );
});

test("fails when the plugin manifest has no URL", () => {
  const { status, output } = run(repo({ manifestUrl: null }));
  assert.equal(status, 1);
  assert.match(output, /mcpServers\.knowledge-mcp\.url is null/);
});

test("fails when the MCP server defaults disagree with the shell", () => {
  const { status, output } = run(
    repo({
      mcpDefaultPort: 8001,
      apiOrigin: "http://127.0.0.1:8000/api/v1",
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /DEFAULT_PORT is "8001", expected 17952/);
  assert.match(
    output,
    /DEFAULT_API_ORIGIN is "http:\/\/127\.0\.0\.1:8000\/api\/v1", expected http:\/\/127\.0\.0\.1:17951\/api\/v1/,
  );
});

test("fails when a content security policy misses the engine", () => {
  const { status, output } = run(
    repo({ csp: "default-src 'self'; connect-src 'self' ipc:" }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /app\.security\.csp does not allow http:\/\/127\.0\.0\.1:17951/,
  );
});

test("fails when a content security policy allows the MCP server", () => {
  const { status, output } = run(
    repo({
      csp: "connect-src 'self' http://127.0.0.1:17951 http://127.0.0.1:17952",
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /app\.security\.csp allows http:\/\/127\.0\.0\.1:17952/);
});

test("does not read a longer port as the engine's", () => {
  const { status, output } = run(
    repo({ csp: "connect-src 'self' http://127.0.0.1:179510" }),
  );
  assert.equal(status, 1);
  assert.match(output, /csp does not allow http:\/\/127\.0\.0\.1:17951/);
});

test("fails when the UI's development origin names another port", () => {
  const { status, output } = run(
    repo({ developmentOrigin: "http://127.0.0.1:8000" }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /backend\.ts: the development origin is "http:\/\/127\.0\.0\.1:8000"/,
  );
});

test("fails when the dev server port is not repeated by the shell and the engine", () => {
  const { status, output } = run(
    repo({
      devUrl: "http://localhost:3000",
      devCsp: "default-src 'self' http://127.0.0.1:17951",
      corsOrigins: ["tauri://localhost"],
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /build\.devUrl is "http:\/\/localhost:3000"/);
  assert.match(output, /devCsp does not allow ws:\/\/localhost:1420/);
  assert.match(
    output,
    /DESKTOP_ORIGINS does not include http:\/\/localhost:1420/,
  );
});

test("fails when a declaring file is missing", () => {
  const dir = mkdtempSync(join(tmpdir(), "ports-"));
  const { status, output } = run(dir);
  assert.equal(status, 1);
  assert.match(output, /launcher\/src-tauri\/src\/ports\.rs: not found/);
});

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import type { TestContext } from "node:test";
import { fileURLToPath } from "node:url";

import { measureInstall } from "./install-report.ts";
import type { Runner } from "./install-report.ts";

const script = fileURLToPath(new URL("./install-report.ts", import.meta.url));
const commit = "a".repeat(40);
const formula = "local/release/knowledge-mcp";
interface Controls {
  installStatus?: number;
  installed?: Array<{ version: string; poured_from_bottle?: boolean }>;
  kbStatus?: number;
  info?: unknown;
}
interface Call {
  command: string;
  args: Array<string>;
  options?: { cwd?: string; log?: string };
}

function harness(context: TestContext) {
  const dir = mkdtempSync(join(tmpdir(), "install-report-"));
  context.after(() => rmSync(dir, { recursive: true, force: true }));
  const prefix = join(dir, "prefix");
  const output = join(dir, "report.json");
  const calls: Array<Call> = [];
  return {
    output,
    calls,
    measure(kind: "source" | "bottle", controls: Controls = {}) {
      const installed = controls.installed ?? [
        { version: "0.2.0", poured_from_bottle: kind === "bottle" },
      ];
      const execute: Runner = (command, args, options) => {
        calls.push({ command, args: [...args], options });
        if (command === "brew") {
          if (args[0] === "install") {
            if (controls.installStatus) {
              throw Object.assign(new Error("brew install failed"), {
                status: controls.installStatus,
              });
            }
            return "";
          }
          if (args[0] === "info") {
            return JSON.stringify(
              controls.info !== undefined
                ? controls.info
                : { formulae: [{ installed }] },
            );
          }
          if (args[0] === "--prefix") return prefix + "\n";
        }
        if (command === join(prefix, "bin/kb")) {
          assert.deepEqual(args, ["--version"]);
          if (controls.kbStatus)
            throw Object.assign(new Error("kb failed"), {
              status: controls.kbStatus,
            });
          return "kb 0.2.0\n";
        }
        if (command === "uname") {
          assert.deepEqual(args, ["-m"]);
          return "arm64\n";
        }
        if (command === "sw_vers") {
          assert.deepEqual(args, ["-productVersion"]);
          return "15.7\n";
        }
        return assert.fail("Unsupported process: " + command);
      };
      let tick = 0;
      return measureInstall(
        {
          formula,
          version: "0.2.0",
          kind,
          tag: "arm64_sequoia",
          commit,
          out: output,
        },
        execute,
        () => 1000 + tick++ * 1500,
      );
    },
    report(): Record<string, unknown> {
      return JSON.parse(readFileSync(output, "utf8")) as Record<
        string,
        unknown
      >;
    },
    cli(kind: string, sourceCommit = commit) {
      return spawnSync(
        process.execPath,
        [
          script,
          "--formula",
          formula,
          "--version",
          "0.2.0",
          "--kind",
          kind,
          "--tag",
          "arm64_sequoia",
          "--commit",
          sourceCommit,
          "--out",
          output,
        ],
        { encoding: "utf8", env: { ...process.env, PATH: dir } },
      );
    },
  };
}

for (const kind of ["source", "bottle"] as const) {
  test(
    kind + " reports capture version, timing and the requested install command",
    (context) => {
      const h = harness(context);
      h.measure(kind);
      const install = h.calls.find(
        (call) => call.command === "brew" && call.args[0] === "install",
      );
      assert.ok(install, "brew install command must be recorded");
      assert.deepEqual(
        install.args,
        kind === "source"
          ? ["install", "--build-from-source", formula]
          : ["install", formula],
      );
      assert.equal(install.options?.log, h.output.replace(/\.json$/, ".log"));
      assert.ok(
        h.calls.some(
          (call) => call.command === "brew" && call.args.includes("--json=v2"),
        ),
        "brew info must provide the installation receipt",
      );
      assert.ok(
        h.calls.some(
          (call) =>
            call.command.endsWith("/bin/kb") && call.args[0] === "--version",
        ),
        "the installed kb must provide its version",
      );
      const report = h.report();
      assert.equal(report.kind, kind);
      assert.equal(report.arch, "arm64");
      assert.equal(report.macos, "15.7");
      assert.equal(report.bottle_tag, "arm64_sequoia");
      assert.equal(report.source_commit, commit);
      assert.equal(report.kb_version, "kb 0.2.0");
      assert.equal(report.dependency_state, "runtime-and-build-preinstalled");
      assert.equal(report.elapsed_seconds, 1.5);
    },
  );
}

test("a failed bottle install propagates its exit status without writing a report", (context) => {
  const h = harness(context);
  assert.throws(
    () => h.measure("bottle", { installStatus: 17 }),
    (error: unknown) =>
      error instanceof Error && "status" in error && error.status === 17,
  );
  assert.equal(existsSync(h.output), false);
  assert.equal(h.calls.length, 1);
  assert.deepEqual(h.calls[0].args, ["install", formula]);
});

const invalidReceipts: Array<[string, Controls["installed"]]> = [
  [
    "source fallback during bottle installation",
    [{ version: "0.2.0", poured_from_bottle: false }],
  ],
  ["a missing poured_from_bottle flag", [{ version: "0.2.0" }]],
  [
    "a different installed version",
    [{ version: "0.1.9", poured_from_bottle: true }],
  ],
  ["no installation", []],
  [
    "multiple installed versions",
    [
      { version: "0.2.0", poured_from_bottle: true },
      { version: "0.1.9", poured_from_bottle: true },
    ],
  ],
];
for (const [label, installed] of invalidReceipts) {
  test("rejects " + label + " without writing a report", (context) => {
    const h = harness(context);
    assert.throws(() => h.measure("bottle", { installed }));
    assert.equal(existsSync(h.output), false);
    assert.equal(
      h.calls.some((call) => call.command.endsWith("/bin/kb")),
      false,
    );
  });
}

test("malformed Homebrew receipts cannot produce a report", (context) => {
  const h = harness(context);
  for (const info of [
    null,
    {},
    { formulae: [] },
    {
      formulae: [
        { installed: [{ version: "0.2.0", poured_from_bottle: true }] },
        { installed: [{ version: "0.2.0", poured_from_bottle: true }] },
      ],
    },
    { formulae: [null] },
    { formulae: [{ installed: "not an array" }] },
    { formulae: [{ installed: [null] }] },
  ]) {
    assert.throws(() => h.measure("bottle", { info }), /installed version/);
    assert.equal(existsSync(h.output), false);
  }
});

test("a bottle pour cannot produce a source timing report", (context) => {
  const h = harness(context);
  assert.throws(() =>
    h.measure("source", {
      installed: [{ version: "0.2.0", poured_from_bottle: true }],
    }),
  );
  assert.equal(existsSync(h.output), false);
});

test("kb version failure cannot produce a report", (context) => {
  const h = harness(context);
  assert.throws(() => h.measure("bottle", { kbStatus: 11 }), /kb failed/);
  assert.equal(existsSync(h.output), false);
});

test("the CLI rejects unsupported install modes and abbreviated commits", (context) => {
  const h = harness(context);
  const unsupported = h.cli("unknown");
  assert.equal(unsupported.status, 1);
  assert.match(unsupported.stderr, /--kind must be source or bottle/);
  const abbreviated = h.cli("bottle", "abc123");
  assert.equal(abbreviated.status, 1);
  assert.match(abbreviated.stderr, /full source commit SHA/);
  assert.equal(existsSync(h.output), false);
});

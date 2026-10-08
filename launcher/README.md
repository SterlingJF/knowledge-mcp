# launcher

The menu-bar app: a React window in a Tauri shell. The shell starts and supervises the engine and MCP server sidecars.

## Layout

```text
launcher/
├── README.md
├── package.json                   check
├── index.html
├── vite.config.ts                 dev server on port 1420; inlines the package version
├── tsconfig.json
├── .oxlintrc.json                 extends ../.oxlintrc.json
├── .oxfmtrc.json
├── prettier.config.js
├── .prettierignore
├── .gitignore
├── scripts/clean-macos-app-state.sh  unregisters and removes apps from local builds; ejects their DMGs
├── scripts/release-build.sh       signs, notarizes, and verifies the DMG; expects built sidecars
├── src/                           the window
│   ├── main.tsx
│   ├── App.tsx                    engine connection; renders VaultSwitcher from components
│   ├── styles.css                 imports components/styles.css
│   ├── globals.d.ts
│   └── lib/                       engine client and shell bridge, with tests
└── src-tauri/                     the Rust shell
    ├── Cargo.toml
    ├── Cargo.lock
    ├── build.rs                   checks the CSP allows the engine port and not the MCP port
    ├── tauri.conf.json            window, CSP, bundle, sidecars
    ├── capabilities/default.json  what the window may do
    ├── entitlements.plist
    ├── icons/
    ├── binaries/                  sidecars from `just build_sidecars`; git-ignored
    ├── src/main.rs
    ├── src/lib.rs                 tray, sidecar supervision, events
    ├── src/ports.rs               engine and MCP server ports
    └── .gitignore
```

## Commands

| Command                      | Purpose                                                                            |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| `pnpm run check`             | Lint, type-check, test, and format-check                                           |
| `just check_launcher`        | From the repo root: the same checks, as in CI                                      |
| `pnpm run dev`               | Start the Vite dev server                                                          |
| `pnpm run build`             | Build, then type-check                                                             |
| `pnpm run serve`             | Preview the build                                                                  |
| `pnpm run test`              | Run Vitest                                                                         |
| `pnpm run typecheck`         | Type-check                                                                         |
| `pnpm run lint`              | Lint with oxlint                                                                   |
| `pnpm run format`            | Format with oxfmt and Prettier                                                     |
| `pnpm run format:check`      | Check formatting                                                                   |
| `pnpm run tauri dev`         | Run the desktop app; run `just build_sidecars` first                               |
| `just build_launcher`        | From the repo root: build the sidecars, then the app and DMG                       |
| `pnpm run clean:macos`       | Unregister and remove apps from local builds; eject their DMGs                     |
| `just clean_macos_app_state` | From the repo root: the same                                                       |
| `just release_launcher`      | From the repo root: build the sidecars, then a signed, notarized, and verified DMG |

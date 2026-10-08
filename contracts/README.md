# contracts

Every contract this project owns or conforms to, with its conformance samples.

## Point of View

Placement follows this project's point of view.

| Folder                 | Direction                                            | Who defines the contract |
| ---------------------- | ---------------------------------------------------- | ------------------------ |
| `project/`             | this project's own modules talk to each other        | this project             |
| `plugins/<name>/`      | outside code plugs into this project                 | this project             |
| `extensions/<target>/` | this project reaches into another project or service | the target               |

When this project plugs into a host, the host calls the contract a plugin. File it under `extensions/`.

## Layout

```text
contracts/
├── README.md
├── package.json                              lint
├── redocly.yaml                              lint policy for every OpenAPI file
├── project/                                  this project's own modules talk to each other
│   └── v1/
│       ├── vault.rest.openapi.yaml           vault lifecycle on the engine's HTTP API
│       ├── <name>.rest.openapi.yaml          request / response
│       ├── <name>.realtime-sse.openapi.yaml  event stream
│       ├── <name>.schema.yaml                data shape
│       └── conformance/
│           ├── pass/<name>.<case>.yaml       must validate against <name>.schema.yaml
│           └── fail/<name>.<case>.yaml       must not validate
├── plugins/<name>/                           outside code plugs into this project
│   └── v1/                                   same shape as project/v1
└── extensions/                               this project reaches into another project
    ├── knowledge-bus/upstream/               protocol, universe, and type guidance, with UPSTREAM.md
    └── <target>/
        ├── upstream/                         the target's spec, vendored read-only, with UPSTREAM.md
        └── v1/                               this project's contracts for the target, same shape as project/v1
```

## Naming

`<name>.<surface>.<kind>.yaml`: the subject, then how it is reached, then the document format. A data shape with no surface is `<name>.schema.yaml`.

A conformance sample `<name>.<case>.yaml` is checked against `<name>.schema.yaml` in the version folder that holds its `conformance/` directory.

## Commands

| Command                              | Purpose                                                                                               |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `pnpm run lint`                      | Lint every `*.openapi.yaml` outside `upstream/` with Redocly                                          |
| `just check_contracts`               | From the repo root: lint, then check every conformance sample                                         |
| `just refresh_knowledge_model <ref>` | From the repo root: copy the knowledge-bus files at `<ref>` into `extensions/knowledge-bus/upstream/` |

## Not Here

| Item                                         | Where it goes                         |
| -------------------------------------------- | ------------------------------------- |
| Code tests for servers, apps, and components | the module that owns the code         |
| Generated models (`*.auto.ts`, `*_auto.py`)  | the module that uses the models       |
| Broker or deployment topology                | infrastructure                        |
| Packaging for another host                   | its own module, named after that host |

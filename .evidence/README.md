# Evidence Archive

Retained local evidence for this repository, analogous to the evidence and artifacts a CI run retains after it finishes. It is local-only: the main repository ignores `/.evidence/`, and this directory is its own nested Git repository with no remote.

## What Belongs Here

Evidence produced while checking, investigating, or changing something:

- screenshots;
- Playwright and other browser output, including HTML reports and traces;
- console and other text evidence, such as browser and server logs;
- performance measurements;
- manifests describing what was captured and under what conditions;
- comparisons, such as pixel diffs and measurement tables.

This archive holds evidence, not scripts or machinery that run checks. Anything that produces evidence belongs in the main repository; only its output belongs here.

## How It Is Organized

Group evidence primarily by the run, investigation, or change that produced it, with evidence types beneath that. Related evidence then stays together as the archive grows, instead of scattering across type-first directories.

Repositories with multiple packages or subsystems should include the relevant scope in the path when that makes the evidence clearer. Evidence spanning several scopes can live under an appropriately named cross-package or integration scope rather than being forced into one package.

For example:

```txt
.evidence/
├── 2026-09-19/
│   ├── viewer/
│   │   ├── check-001/
│   │   │   ├── screenshots/
│   │   │   │   ├── overview-idle-light.png
│   │   │   │   └── overview-selected-light.png
│   │   │   ├── playwright/
│   │   │   │   └── report/
│   │   │   ├── performance/
│   │   │   │   └── interaction-timing.json
│   │   │   ├── console/
│   │   │   │   └── browser.log
│   │   │   └── manifest.json
│   │   │
│   │   └── slice-43/
│   │       ├── screenshots/
│   │       ├── performance/
│   │       └── manifest.json
│   │
│   ├── api/
│   │   └── check-001/
│   │       ├── console/
│   │       └── manifest.json
│   │
│   └── integration/
│       └── check-002/
│           ├── playwright/
│           ├── console/
│           └── manifest.json
│
└── 2026-09-20/
    └── ...
```

Then a particular screenshot has a natural trail:

```txt
2026-09-19/viewer/check-001/screenshots/overview-selected-light.png
2026-09-19/viewer/slice-43/screenshots/overview-selected-light.png
2026-09-20/viewer/check-001/screenshots/overview-selected-light.png
```

Same for a performance measurement:

```txt
2026-09-19/viewer/check-001/performance/interaction-timing.json
2026-09-19/viewer/slice-43/performance/interaction-timing.json
2026-09-20/viewer/check-001/performance/interaction-timing.json
```

And console evidence can have trails within different scopes:

```txt
2026-09-19/viewer/check-001/console/browser.log
2026-09-19/api/check-001/console/server.log
2026-09-19/integration/check-002/console/browser.log
```

These examples are illustrative. They show the shape of the archive, not directories that must exist.

## What Each Path Segment Means

- `.evidence/` — what the archive is for;
- the date — when the evidence was produced;
- the scope, when used — the relevant package, subsystem, or cross-package concern;
- the run, investigation, or change — why the evidence was produced;
- the subdirectories — the type of evidence.

## The Nested Repository

`.evidence/` is its own Git repository, so the evidence archive keeps its own local history without polluting the main repository's history. Conceptually its history might be:

```txt
commit A
  Add baseline viewer evidence

commit B
  Add viewer slice 35 evidence

commit C
  Add API check evidence

commit D
  Add integration check evidence

commit E
  Add viewer slice 43 comparison evidence
```

So there are actually two complementary trails:

Filesystem trail

```txt
.evidence/
  2026-09-19/
    viewer/
      slice-35/
      slice-42/
      slice-43/
    api/
      check-001/
    integration/
      check-002/
```

tells you what evidence belongs together and which part of the repository it concerns.

Git history of `.evidence/`

```txt
A → B → C → D → E
```

tells you when those evidence sets entered the archive and lets you inspect differences between points in its history.

## Before and After

For normal chronological evidence, the previous equivalent evidence set is the implicit before state; do not duplicate it under a new `before/` directory by default.

For example:

```txt
.evidence/
└── 2026-09-19/
    └── viewer/
        ├── slice-42/
        │   └── screenshots/
        ├── slice-43/
        │   └── screenshots/
        └── slice-44/
            └── screenshots/
```

Here, the relevant prior comparable capture is the natural before-state for the later evidence.

Use an explicit controlled before/after pair only when both were deliberately captured together under matched conditions for a specific investigation. For example:

```txt
.evidence/
└── 2026-09-19/
    └── viewer/
        └── investigation-43/
            ├── before/
            │   ├── screenshots/
            │   ├── performance/
            │   └── console/
            ├── after/
            │   ├── screenshots/
            │   ├── performance/
            │   └── console/
            ├── comparison/
            │   ├── pixel-diff/
            │   └── measurements.json
            └── manifest.json
```

Or, when there isn't naturally a before/after:

```txt
.evidence/
└── 2026-09-19/
    └── viewer/
        └── check-1432/
            ├── screenshots/
            ├── playwright/
            ├── performance/
            ├── console/
            └── manifest.json
```

And evidence whose meaning is specifically cross-package can be scoped accordingly:

```txt
.evidence/
└── 2026-09-19/
    └── integration/
        └── check-1433/
            ├── playwright/
            ├── performance/
            ├── console/
            └── manifest.json
```

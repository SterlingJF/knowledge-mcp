// knowledge-mcp MCP App tokens: the single source for every storyboard, foundations and components frame.
// Names are the MCP Apps host style variables. Values are Claude's documented values
// (claude.com/docs/connectors/building/mcp-apps/design-guidelines#style-variables), used as fallbacks
// so a card outside a host still reads; inside Claude the host's own values apply.
window.KMT = {
  source:
    "https://claude.com/docs/connectors/building/mcp-apps/design-guidelines#style-variables",
  color: {
    light: {
      "--color-background-primary": "#FFFFFF",
      "--color-background-secondary": "#F5F4ED",
      "--color-background-tertiary": "#FAF9F5",
      "--color-background-inverse": "#141413",
      "--color-background-info": "#D6E4F6",
      "--color-background-success": "#E9F1DC",
      "--color-background-warning": "#F6EEDF",
      "--color-background-danger": "#F7ECEC",
      "--color-text-primary": "#141413",
      "--color-text-secondary": "#3D3D3A",
      "--color-text-tertiary": "#73726C",
      "--color-text-inverse": "#FFFFFF",
      "--color-text-info": "#3266AD",
      "--color-text-success": "#265B19",
      "--color-text-warning": "#5A4815",
      "--color-text-danger": "#7F2C28",
      "--color-border-primary": "rgba(31,30,29,.4)",
      "--color-border-secondary": "rgba(31,30,29,.3)",
      "--color-border-tertiary": "rgba(31,30,29,.15)",
      "--color-ring-primary": "rgba(20,20,19,.7)",
    },
    dark: {
      "--color-background-primary": "#30302E",
      "--color-background-secondary": "#262624",
      "--color-background-tertiary": "#141413",
      "--color-background-inverse": "#FAF9F5",
      "--color-background-info": "#253E5F",
      "--color-background-success": "#1B4614",
      "--color-background-warning": "#483A0F",
      "--color-background-danger": "#602A28",
      "--color-text-primary": "#FAF9F5",
      "--color-text-secondary": "#C2C0B6",
      "--color-text-tertiary": "#9C9A92",
      "--color-text-inverse": "#141413",
      "--color-text-info": "#80AADD",
      "--color-text-success": "#7AB948",
      "--color-text-warning": "#D1A041",
      "--color-text-danger": "#EE8884",
      "--color-border-primary": "rgba(222,220,209,.4)",
      "--color-border-secondary": "rgba(222,220,209,.3)",
      "--color-border-tertiary": "rgba(222,220,209,.15)",
      "--color-ring-primary": "rgba(250,249,245,.7)",
    },
  },
  // What each colour is for. A component names the role, never a value.
  roles: [
    [
      "--color-background-tertiary",
      "Host chat ground: the card is transparent, so this shows through",
    ],
    ["--color-background-primary", "Chips, secondary buttons"],
    ["--color-background-secondary", "Notes, neutral badges, skeletons"],
    ["--color-background-inverse", "Primary button"],
    ["--color-text-primary", "Titles, body, cell text"],
    [
      "--color-text-tertiary",
      "Eyebrows, meta, captions, current text, column heads",
    ],
    ["--color-border-tertiary", "Row dividers, chips"],
    ["--color-border-secondary", "Segmented choice outline"],
    [
      "--color-text-tertiary",
      "Also the unticked box edge: 3:1 as a control boundary",
    ],
    ["--color-ring-primary", "Focus ring on every control"],
    ["warning", "Waiting on you: Needs your OK, Nothing saved, Your choice"],
    ["success", "Done and recorded: Saved, Approved, Created, Moved, Applied"],
    [
      "danger",
      "Refused or stopped, with the reason: Can’t undo safely, Checker refused",
    ],
    ["info", "Reserved: nothing uses it while loading is a skeleton"],
  ],
  font: {
    "--font-sans":
      '"Anthropic Sans", ui-sans-serif, system-ui, -apple-system, sans-serif',
    "--font-mono": "ui-monospace, monospace",
    "--font-weight-normal": "400",
    "--font-weight-semibold": "600",
    "--font-text-xs-size": "12px",
    "--font-text-xs-line-height": "1.4",
    "--font-text-sm-size": "14px",
    "--font-text-sm-line-height": "1.4",
    "--font-heading-md-size": "16px",
    "--font-heading-md-line-height": "1.4",
  },
  // Claude: "the three-level size scale of heading, body, and caption, and the two weights of regular and emphasized".
  type: [
    [
      "--font-heading-md",
      "semibold",
      "Heading: card title",
      "Focus the proposal on retiring the evening build",
    ],
    [
      "--font-text-sm",
      "normal",
      "Body: cell text, notes, buttons (emphasized)",
      "7 of 9 evening runs hit the 6-hour limit",
    ],
    [
      "--font-text-xs",
      "normal",
      "Caption: eyebrow (uppercase), meta, badges, column heads, C-numbers, mono paths",
      "Waits for you because it changes cache-proposal.md.",
    ],
  ],
  radius: {
    "--border-radius-xs": "4px",
    "--border-radius-sm": "6px",
    "--border-radius-md": "8px",
    "--border-radius-lg": "10px",
    "--border-radius-xl": "12px",
    "--border-radius-full": "9999px",
  },
  radiusUse: {
    "--border-radius-xs": "Tick box",
    "--border-radius-sm": "Chips, segmented choice",
    "--border-radius-md": "Buttons",
    "--border-radius-lg": "Notes, diff, skeleton blocks",
    "--border-radius-xl": "Not ours: the host’s bordered frame",
    "--border-radius-full": "Badges, evidence marks",
  },
  border: { "--border-width-regular": "0.5px" },
  // Ours, not host variables: spacing has no host equivalent. A 4px base; 2px only inside badges and chips.
  space: {
    "--km-space-1": "2px",
    "--km-space-2": "4px",
    "--km-space-3": "6px",
    "--km-space-4": "8px",
    "--km-space-5": "12px",
    "--km-space-6": "16px",
    "--km-space-7": "24px",
  },
  spaceUse: {
    "--km-space-1": "Block padding inside a badge or chip",
    "--km-space-2": "Icon to its label",
    "--km-space-3": "Block padding inside a button",
    "--km-space-4": "Inline padding of a badge, row padding",
    "--km-space-5": "Inline padding of a button or note",
    "--km-space-6": "Gap from any edge (safe area)",
    "--km-space-7": "Between sections of the full view",
  },
  // Spacing by role: components use these, never a bare step, so every card keeps one rhythm.
  // A gap between groups is twice the gap inside one (proximity), and a group's header sits closer to what follows it.
  gap: {
    "--km-gap-tight": "var(--km-space-2)",
    "--km-gap-inline": "var(--km-space-4)",
    "--km-gap-row": "var(--km-space-4)",
    "--km-gap-group": "var(--km-space-6)",
    "--km-gap-section": "var(--km-space-7)",
  },
  gapUse: {
    "--km-gap-tight":
      "Inside one heading block: eyebrow to title, title to meta",
    "--km-gap-inline":
      "Between items on one line: chip and text, chip and chip, button and button",
    "--km-gap-row":
      "Between rows of one group: summary rows, table rows, list rows",
    "--km-gap-group":
      "Between groups of a card: header, summary, note, actions",
    "--km-gap-section": "Between sections of the full view",
  },
  motion: {
    "--km-pulse": "1.6s ease-out infinite",
    "--km-shimmer": "1.4s ease-in-out infinite",
  },
  touch: { "--km-target": "44px" },
  // Fixed sizes with no host variable: icons, the tick box, the pulse dot, the summary label column, a skeleton row.
  size: {
    "--km-icon": "13px",
    "--km-icon-sm": "11px",
    "--km-check": "15px",
    "--km-check-border": "1.5px",
    "--km-dot": "7px",
    "--km-label-col": "max-content",
    "--km-row": "28px",
    "--km-underline": "2px",
  },
  // One focus ring, one tracking, four opacities: each used by more than one part.
  effect: {
    "--km-focus-ring":
      "0 0 0 2px var(--color-background-primary), 0 0 0 4px var(--color-ring-primary)",
    "--km-eyebrow-tracking": "0.07em",
    "--km-opacity-hover": "0.88",
    "--km-opacity-dim": "0.55",
    "--km-opacity-disabled": "0.4",
  },
  layout: {
    min: "From 320px to fullscreen, by container queries, no fixed breakpoints",
    header:
      "Under 480px of container: the title takes the full width; status and Full view follow it",
    summary:
      "Under 420px of container: each summary label sits above its value",
    narrow: "Under 560px of container: table rows stack",
  },
};
("ok");

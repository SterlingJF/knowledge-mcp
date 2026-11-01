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
  // What each host colour is for, by the shadcn name that carries it. A component names the shadcn role, never a value.
  roles: [
    [
      "--color-background-tertiary",
      "Host chat ground: the card is transparent, so this shows through",
    ],
    [
      "--color-background-inverse",
      "primary: the one filled action, ticked boxes, the chosen option",
    ],
    [
      "--color-background-secondary",
      "muted, secondary, accent: notes, neutral badges, hover, skeletons",
    ],
    ["--color-text-primary", "foreground: titles, body, cell text"],
    [
      "--color-text-tertiary",
      "muted-foreground: eyebrows, meta, captions, current text, column heads",
    ],
    ["--color-border-tertiary", "border: row dividers, outline badges"],
    [
      "--color-border-secondary",
      "input: outline buttons, tick boxes, the option group",
    ],
    ["--color-ring-primary", "ring: the focus ring on every control"],
    [
      "--color-text-danger",
      "destructive: refused or stopped, removed diff lines",
    ],
    [
      "success",
      "Done and recorded: Saved, Approved, Created, Moved, Applied; added diff lines",
    ],
    ["warning", "Waiting on you: Needs your OK, Nothing saved, Your choice"],
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
    "--border-radius-xs": "Not used",
    "--border-radius-sm": "rounded-sm: tick box",
    "--border-radius-md":
      "rounded-md, shadcn's --radius: buttons, option group",
    "--border-radius-lg": "rounded-lg: notes, diff, skeleton blocks",
    "--border-radius-xl": "Not ours: the host's bordered frame",
    "--border-radius-full": "rounded-full: badges",
  },

  border: { "--border-width-regular": "0.5px" },
  // Everything without a host variable comes from Tailwind's defaults: spacing on its 4px scale
  // (gap-1 4px, gap-2 8px, gap-4 16px, gap-6 24px), icon sizes, opacity, the focus ring and animate-pulse.
  // shadcn's names point at the host roles below; nothing here is the app's own.
  shadcn: {
    "--background": "transparent",
    "--foreground": "var(--color-text-primary)",
    "--card": "transparent",
    "--card-foreground": "var(--color-text-primary)",
    "--popover": "var(--color-background-primary)",
    "--popover-foreground": "var(--color-text-primary)",
    "--primary": "var(--color-background-inverse)",
    "--primary-foreground": "var(--color-text-inverse)",
    "--secondary": "var(--color-background-secondary)",
    "--secondary-foreground": "var(--color-text-primary)",
    "--muted": "var(--color-background-secondary)",
    "--muted-foreground": "var(--color-text-tertiary)",
    "--accent": "var(--color-background-secondary)",
    "--accent-foreground": "var(--color-text-primary)",
    "--destructive": "var(--color-text-danger)",
    "--border": "var(--color-border-tertiary)",
    "--input": "var(--color-border-secondary)",
    "--ring": "var(--color-ring-primary)",
    "--radius": "var(--border-radius-md)",
    // Status colours, added the way shadcn's theming adds a colour: a surface and its foreground.
    "--success": "var(--color-background-success)",
    "--success-foreground": "var(--color-text-success)",
    "--warning": "var(--color-background-warning)",
    "--warning-foreground": "var(--color-text-warning)",
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

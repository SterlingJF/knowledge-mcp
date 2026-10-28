// Development gallery: every *.gallery.tsx story in light and dark side by side, like the Components page sheets.
// A story file exports a default object: { id: "K01", name: "Badge", stories: { "Waiting": <Badge … /> } }.
// Not part of the app build: vite build only reads index.html.

import { StrictMode } from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";

import "../styles.css";

type Sheet = { id: string; name: string; stories: Record<string, ReactNode> };

const modules = import.meta.glob<{ default: Sheet }>("../**/*.gallery.tsx", {
  eager: true,
});
const sheets = Object.values(modules)
  .map((module) => module.default)
  .sort((a, b) => a.id.localeCompare(b.id));

function Pane({ theme, sheet }: { theme: "light" | "dark"; sheet: Sheet }) {
  return (
    <div
      data-theme={theme}
      style={{
        colorScheme: theme,
        background: "var(--color-background-tertiary)",
        padding: 24,
      }}
    >
      {Object.entries(sheet.stories).map(([label, story]) => (
        <div
          key={label}
          style={{
            display: "grid",
            gridTemplateColumns: "160px 1fr",
            gap: 12,
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <span
            style={{
              color: "var(--color-text-tertiary)",
              fontSize: "var(--font-text-xs-size)",
            }}
          >
            {label}
          </span>
          <div>{story}</div>
        </div>
      ))}
    </div>
  );
}

function Gallery() {
  return (
    <main style={{ padding: 32, display: "grid", gap: 32 }}>
      {sheets.length === 0 && (
        <p>No stories yet: add a *.gallery.tsx beside a component.</p>
      )}
      {sheets.map((sheet) => (
        <section key={sheet.id} id={sheet.id}>
          <h2
            style={{
              fontSize: "var(--font-heading-md-size)",
              margin: "0 0 12px",
            }}
          >
            {sheet.id} · {sheet.name}
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <Pane theme="light" sheet={sheet} />
            <Pane theme="dark" sheet={sheet} />
          </div>
        </section>
      ))}
    </main>
  );
}

const root = document.getElementById("root");
if (!root) throw new Error("gallery.html has no #root");
createRoot(root).render(
  <StrictMode>
    <Gallery />
  </StrictMode>,
);

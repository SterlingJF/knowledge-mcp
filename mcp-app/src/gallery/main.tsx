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
    <div data-theme={theme} data-pane className="p-6">
      {Object.entries(sheet.stories).map(([label, story]) => (
        <div key={label} className="mb-3 flex items-center gap-3">
          <span className="w-40 shrink-0 text-xs text-muted-foreground">
            {label}
          </span>
          <div className="min-w-0 flex-1">{story}</div>
        </div>
      ))}
    </div>
  );
}

function Gallery() {
  return (
    <main className="grid gap-8 p-8">
      {sheets.length === 0 && (
        <p>No stories yet: add a *.gallery.tsx beside a component.</p>
      )}
      {sheets.map((sheet) => (
        <section key={sheet.id} id={sheet.id}>
          <h2 className="mb-3 text-base">
            {sheet.id} · {sheet.name}
          </h2>
          <div className="grid overflow-hidden rounded-xl">
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

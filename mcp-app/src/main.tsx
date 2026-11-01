import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { CardView } from "./cards/registry";
import { CardHostProvider, useCardHost } from "./bridge/bridge";

import "./styles.css";

// Each cards/*-card.tsx registers itself on import, so a new card needs no edit here.
import.meta.glob("./cards/*-card.tsx", { eager: true });

function Card() {
  const { result } = useCardHost();
  return <CardView result={result} />;
}

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root");

createRoot(root).render(
  <StrictMode>
    <CardHostProvider>
      <Card />
    </CardHostProvider>
  </StrictMode>,
);

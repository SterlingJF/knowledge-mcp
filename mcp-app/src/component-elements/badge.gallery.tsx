import type { ReactNode } from "react";

import { badge } from "@/copy/en";
import { Badge } from "./badge";

const Row = ({ children }: { children: ReactNode }) => (
  <span style={{ display: "inline-flex", gap: "var(--km-space-4)" }}>
    {children}
  </span>
);

export default {
  id: "K01",
  name: "Badge",
  stories: {
    "Waiting · pulse": (
      <Row>
        <Badge tone="waiting">{badge.waiting.needsOk}</Badge>
        <Badge tone="waiting">{badge.waiting.nothingSaved}</Badge>
      </Row>
    ),
    Done: (
      <Row>
        <Badge tone="done">{badge.done.saved}</Badge>
        <Badge tone="done">{badge.done.approved}</Badge>
      </Row>
    ),
    Refused: <Badge tone="refused">{badge.refused.cantUndo}</Badge>,
    Neutral: (
      <Row>
        <Badge tone="neutral">{badge.neutral.notSaved}</Badge>
        <Badge tone="neutral">{badge.neutral.noType}</Badge>
      </Row>
    ),
    "Reduced motion (set in OS)": (
      <Badge tone="waiting">{badge.waiting.needsOk}</Badge>
    ),
  },
};

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root");

// Card 0.3 replaces this with the host bridge and the card router.
createRoot(root).render(
  <StrictMode>
    <p>knowledge-mcp</p>
  </StrictMode>,
);

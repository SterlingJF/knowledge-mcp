import { useState } from "react";

import { evidence, label } from "@/copy/en";
import { SegmentedChoice } from "./segmented-choice";

function Two() {
  const [value, setValue] = useState<"current" | "proposed">("proposed");
  const options = [
    { value: "current", label: label.current },
    { value: "proposed", label: label.proposed },
  ] as const;
  return <SegmentedChoice aria-label={label.changes} options={options} value={value} onValueChange={setValue} />;
}

function Three() {
  const [value, setValue] = useState<"supported" | "partly" | "conflicting">("supported");
  const options = [
    { value: "supported", label: evidence.supported },
    { value: "partly", label: evidence.partly },
    { value: "conflicting", label: evidence.conflicting },
  ] as const;
  return <SegmentedChoice aria-label={label.evidence} options={options} value={value} onValueChange={setValue} />;
}

export default {
  id: "K11",
  name: "Segmented choice",
  stories: { "Two options": <Two />, "Three options": <Three /> },
};

import { useState } from "react";

import { decision, evidence, label } from "@/copy/en";
import { SegmentedChoice } from "./segmented-choice";

function Two({ start }: { start: "accept" | "drop" | null }) {
  const [value, setValue] = useState(start);
  const options = [
    { value: "accept", label: decision.accept },
    { value: "drop", label: decision.drop },
  ] as const;
  return (
    <SegmentedChoice
      aria-label={label.changes}
      options={options}
      value={value}
      onValueChange={setValue}
    />
  );
}

function Three() {
  const [value, setValue] = useState<"supported" | "partly" | "conflicting">(
    "supported",
  );
  const options = [
    { value: "supported", label: evidence.supported },
    { value: "partly", label: evidence.partly },
    { value: "conflicting", label: evidence.conflicting },
  ] as const;
  return (
    <SegmentedChoice
      aria-label={label.evidence}
      options={options}
      value={value}
      onValueChange={setValue}
    />
  );
}

export default {
  id: "K11",
  name: "Segmented choice",
  stories: {
    Undecided: <Two start={null} />,
    Chosen: <Two start="accept" />,
    "Three options": <Three />,
  },
};

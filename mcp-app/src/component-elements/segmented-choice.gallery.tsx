import { useState } from "react";

import { decision, evidence, label } from "@/copy/en";

import { SegmentedChoice } from "./segmented-choice";
import type { SegmentOption } from "./segmented-choice";

const sets: Record<string, SegmentOption<string>[]> = {
  one: [{ value: "skip", label: decision.skip }],
  two: [
    { value: "accept", label: decision.accept },
    { value: "drop", label: decision.drop },
  ],
  three: [
    { value: "supported", label: evidence.supported },
    { value: "partly", label: evidence.partly },
    { value: "conflicting", label: evidence.conflicting },
  ],
  long: [
    { value: "a", label: "Link to Decisions/2026-10-28 retire evening build" },
    { value: "b", label: "Link to Calendar/Meetings/2026-10-27 build review" },
  ],
  five: ["Inbox/", "Meetings/", "Decisions/", "Proposals/", "Archive/"].map(
    (f) => ({ value: f, label: f }),
  ),
};

function Live({ set, start = null }: { set: string; start?: string | null }) {
  const [value, setValue] = useState(start);
  return (
    <SegmentedChoice
      aria-label={label.changes}
      options={sets[set]}
      value={value}
      onValueChange={setValue}
    />
  );
}

const at = (w: "727" | "360", set: string, start?: string) => (
  <div
    className={w === "727" ? "w-[727px] max-w-full" : "w-[360px] max-w-full"}
  >
    <Live set={set} start={start} />
  </div>
);

export default {
  id: "K11",
  name: "Segmented choice",
  stories: {
    "1 option at 727px": at("727", "one"),
    "1 option at 360px": at("360", "one", "skip"),
    "2 options at 727px": at("727", "two"),
    "2 options at 360px": at("360", "two", "accept"),
    "3 options at 727px": at("727", "three", "supported"),
    "3 options at 360px": at("360", "three"),
    "2 long options at 727px": at("727", "long"),
    "2 long options at 360px": at("360", "long", "a"),
    "5 options at 727px": at("727", "five", "Meetings/"),
    "5 options at 360px": at("360", "five"),
  },
};

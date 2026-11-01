import { PathChip, SourceChip } from "./chips";

const row = "flex flex-wrap items-center gap-km-gap-inline";

export default {
  id: "K04",
  name: "Chips: source and path",
  stories: {
    // A name with no space, "/" or room to fit: it breaks only because it is wider than the line.
    "Long name at 320px": (
      <div className="w-[320px] border-hairline border-dashed border-input">
        <PathChip path="quarterly-build-operations-retrospective-final.md" />
      </div>
    ),
    "Line source": (
      <SourceChip source={{ file: "meeting-notes.md", line_number: 15 }} />
    ),
    "Place source": (
      <div className="grid justify-items-start gap-km-gap-inline">
        <SourceChip
          source={{ file: "build-timings.xlsx", place: "Evening!A2:D10" }}
        />
        <SourceChip
          source={{ file: "cache-rollout-review.pptx", place: "slide 7" }}
        />
      </div>
    ),
    "Person source": (
      <SourceChip source={{ said: "a proposal … on its own" }} />
    ),
    "Same file, another line": (
      <div className={row}>
        <SourceChip source={{ file: "meeting-notes.md", line_number: 11 }} />
        <SourceChip
          continuation
          source={{ file: "meeting-notes.md", line_number: 19 }}
        />
      </div>
    ),
    "File in scope": <PathChip path="cache-proposal.md" />,
    "Folder in scope": <PathChip folder path="~/Notes/Build Operations" />,
  },
};

import { action, badge, frozen, line } from "@/copy/en";
import { HarnessFrame, exampleMeta } from "./card-shell.harness";
import { CardShell } from "./card-shell";
import type { CardAction, CardShellProps } from "./card-shell";

const actions: CardAction[] = [
  {
    label: action.save("C1–C4"),
    message: "",
    frozenLine: frozen.approved,
    variant: "primary",
  },
  { label: action.notNow, message: "", frozenLine: frozen.notSaved },
];

const base: CardShellProps = {
  eyebrow: "Proposed changes",
  title: "Focus the proposal on retiring the evening build",
  meta: exampleMeta,
  badge: { tone: "waiting", label: badge.waiting.nothingSaved },
  why: line.waitsBecause("cache-proposal.md"),
  actions,
};

export default {
  id: "P01",
  name: "Card shell",
  stories: {
    Live: (
      <HarnessFrame>
        <CardShell {...base} onFullView={() => {}} />
      </HarnessFrame>
    ),
    "Narrow (320px)": (
      <div className="max-w-xs">
        <HarnessFrame>
          <CardShell {...base} onFullView={() => {}} />
        </HarnessFrame>
      </div>
    ),
    Frozen: (
      <HarnessFrame>
        <CardShell
          {...base}
          eyebrow="Change"
          badge={{ tone: "done", label: badge.done.approved }}
          state="frozen"
          frozenLine={frozen.approved}
        />
      </HarnessFrame>
    ),
    Replaced: (
      <HarnessFrame>
        <CardShell {...base} eyebrow="Change" state="replaced" />
      </HarnessFrame>
    ),
    "Flat (inside the full view)": <CardShell {...base} flat />,
  },
};

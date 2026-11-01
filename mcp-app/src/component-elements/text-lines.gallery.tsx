import { Caption, CurrentText, Eyebrow } from "./text-lines";

export default {
  id: "K07",
  name: "Text lines",
  stories: {
    Eyebrow: <Eyebrow>Proposed changes</Eyebrow>,
    Caption: (
      <Caption>Waits for you because it changes cache-proposal.md.</Caption>
    ),
    "Current text": (
      <CurrentText label="Title">Build schedule and cache rollout</CurrentText>
    ),
  },
};

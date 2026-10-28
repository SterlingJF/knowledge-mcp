import {
  CurrentText,
  Eyebrow,
  FrozenLine,
  Meta,
  Title,
  WhyLine,
} from "./text-lines";

export default {
  id: "K07",
  name: "Text lines",
  stories: {
    Eyebrow: <Eyebrow>Proposed changes</Eyebrow>,
    Title: <Title>Focus the proposal on retiring the evening build</Title>,
    Meta: (
      <Meta>
        Design proposal · for maintainers deciding whether to accept it
      </Meta>
    ),
    "Why line": (
      <WhyLine className="mt-0">
        Waits for you because it changes cache-proposal.md.
      </WhyLine>
    ),
    "Frozen line": <FrozenLine className="mt-0">You approved this.</FrozenLine>,
    "Current text": (
      <CurrentText label="Title">Build schedule and cache rollout</CurrentText>
    ),
  },
};

import { ChangeNumber, SelectAll } from "./change-number";

const noop = () => {};

export default {
  id: "K05",
  name: "Change number and tick box",
  stories: {
    Kept: <ChangeNumber n={1} kept onKeptChange={noop} />,
    "Left out": <ChangeNumber n={1} kept={false} onKeptChange={noop} />,
    "Frozen card (no box)": <ChangeNumber n={1} />,
    "Header · all selected": (
      <SelectAll keptCount={3} total={3} onChange={noop} />
    ),
    "Header · some left out": (
      <SelectAll keptCount={2} total={3} onChange={noop} />
    ),
  },
};

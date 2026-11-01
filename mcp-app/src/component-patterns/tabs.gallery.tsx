import { Tabs } from "./tabs";

const tabs = [
  {
    value: "moves",
    label: "Moves",
    count: 3,
    content: <p>Each file and where it goes.</p>,
  },
  {
    value: "links",
    label: "Links",
    count: 5,
    content: <p>Each link before and after.</p>,
  },
];

export default {
  id: "K14",
  name: "Tabs",
  stories: {
    "First tab": <Tabs tabs={tabs} />,
    "Second tab": <Tabs tabs={tabs} defaultValue="links" />,
  },
};

import { EvidenceMark } from "../evidence-mark";

export default {
  id: "K03",
  name: "Evidence mark",
  stories: {
    Supported: <EvidenceMark mark="supported" />,
    "Partly answered": <EvidenceMark mark="partly" />,
    Conflicting: <EvidenceMark mark="conflicting" />,
    "Suggested (your words)": <EvidenceMark mark="suggested" />,
  },
};

import { KeyValue } from "./key-value";

export default {
  id: "K08",
  name: "Key–value grid",
  stories: {
    "Three rows": (
      <KeyValue
        className="mt-0"
        rows={[
          {
            label: "Reader",
            value: "Maintainers deciding whether to accept it",
          },
          { label: "Guidance", value: "product-dev · Design proposal" },
          {
            label: "Since then",
            value: (
              <>
                <b>4 new files, 1 moved</b> · 3 can be filed by your conventions
              </>
            ),
          },
        ]}
      />
    ),
  },
};

// K11 Choice: pick one of 2 or more answers. Core RadioGroup, one option per line, each radio inside its label.
import { Label } from "@/component-core/label";
import { RadioGroup, RadioGroupItem } from "@/component-core/radio-group";

export type SegmentOption<V extends string> = { value: V; label: string };

export type SegmentedChoiceProps<V extends string> = {
  /** Two or more options, all visible. A single yes-or-no answer is a K05 tick box instead. */
  options: readonly SegmentOption<V>[];
  /** null while undecided: nothing is selected. */
  value: V | null;
  onValueChange: (value: V) => void;
  "aria-label": string;
  className?: string;
};

export function SegmentedChoice<V extends string>({
  options,
  value,
  onValueChange,
  className,
  "aria-label": ariaLabel,
}: SegmentedChoiceProps<V>) {
  if (options.length < 2)
    throw new Error("SegmentedChoice takes 2 or more options");
  return (
    <RadioGroup
      aria-label={ariaLabel}
      value={value}
      onValueChange={(v) => onValueChange(v as V)}
      className={className}
    >
      {options.map((option) => (
        <Label key={option.value}>
          <RadioGroupItem value={option.value} />
          {option.label}
        </Label>
      ))}
    </RadioGroup>
  );
}

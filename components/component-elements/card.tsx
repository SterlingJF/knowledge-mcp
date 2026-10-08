// File: components/component-elements/card.tsx
//
import {
  CardAction,
  Card as CardBase,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../component-core/card";
import { cn } from "../lib/utils";

// Tailwind's extractor misses `]` against `${` in template literals.
export function Card({ className, ...props }: Parameters<typeof CardBase>[0]) {
  return (
    <CardBase
      className={cn("[--card-spacing:var(--base-card-padding)]", className)}
      {...props}
    />
  );
}

export {
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
};

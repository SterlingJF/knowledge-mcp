// Picks the card for a tool result by its schema, such as knowledge-mcp/proposal/1.
// A result with no card here draws nothing: the host still shows the tool's text card.

import type { ComponentType } from "react";

import type { ToolResult } from "@/host/host";

export type CardProps = { result: ToolResult };

const cards = new Map<string, ComponentType<CardProps>>();

export function registerCard(
  schema: string,
  card: ComponentType<CardProps>,
): void {
  cards.set(schema, card);
}

export function cardFor(
  result: ToolResult | null,
): ComponentType<CardProps> | null {
  const schema = result?.schema;
  return typeof schema === "string" ? (cards.get(schema) ?? null) : null;
}

export function CardView({ result }: { result: ToolResult | null }) {
  const Card = cardFor(result);
  return Card && result ? <Card result={result} /> : null;
}

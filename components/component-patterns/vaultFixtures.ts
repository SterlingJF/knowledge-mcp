// File: components/component-patterns/vaultFixtures.ts

import type { Vault } from "../lib/types";

const OPENED = 1788036055884;

export const vault = (
  overrides: Partial<Vault> & Pick<Vault, "id" | "name">,
): Vault => ({
  path: `/Users/sterling/vaults/${overrides.name}`,
  lastOpened: OPENED,
  open: false,
  available: true,
  ...overrides,
});

export const vaults: Array<Vault> = [
  vault({ id: "a1", name: "product-decisions", open: true }),
  vault({ id: "b2", name: "knowledge-bus", lastOpened: OPENED - 1000 }),
  vault({
    id: "c3",
    name: "scratch",
    path: "/Users/sterling/Desktop/side_projects/scratch",
    lastOpened: OPENED - 2000,
  }),
];

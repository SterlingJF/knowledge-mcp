// Data shapes the patterns render. The app supplies the values.

export type Vault = {
  id: string;
  /** The folder's own name. A vault carries no name of its own. */
  name: string;
  path: string;
  lastOpened: number;
  open: boolean;
  /** False when the folder has been moved or deleted since it was last opened. */
  available: boolean;
};

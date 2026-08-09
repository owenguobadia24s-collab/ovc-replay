import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import styles from "../workspace/WorkspaceFrame.module.css";

export type PaletteAction = { id: string; label: string; detail: string; run: () => void };

export function CommandPalette({ actions }: { actions: PaletteAction[] }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setOpen((value) => !value); }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
  return <Dialog.Root open={open} onOpenChange={setOpen}>
    <Dialog.Trigger asChild><button className={styles.commandButton} type="button" aria-label="Open navigation command palette">⌘ Ctrl+K</button></Dialog.Trigger>
    <Dialog.Portal><Dialog.Overlay className={styles.paletteOverlay}/><Dialog.Content className={styles.palette} aria-describedby="palette-description">
      <Dialog.Title>Navigation commands</Dialog.Title><Dialog.Description id="palette-description">Fixture-only navigation and presentation controls. No command mutates evidence or authority.</Dialog.Description>
      <div className={styles.paletteActions}>{actions.map((action) => <button key={action.id} type="button" onClick={() => { action.run(); setOpen(false); }}><strong>{action.label}</strong><span>{action.detail}</span></button>)}</div>
      <Dialog.Close asChild><button className={styles.paletteClose} type="button">Close</button></Dialog.Close>
    </Dialog.Content></Dialog.Portal>
  </Dialog.Root>;
}

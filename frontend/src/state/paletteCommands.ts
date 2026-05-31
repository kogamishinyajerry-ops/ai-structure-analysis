// FM-04a Phase 25 B — Cmd-K palette command list extracted from
// App.tsx for LOC discipline. Pure-function builder taking typed
// action callbacks and returning the same Command[] the palette
// consumes. ZERO behavior change.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

import type { Command, CommandCategory } from '../commands/registry';
import type { MaterialRecord } from '../materialsClient';

/** Callback bag for palette command handlers. Keeping this typed at
 * the bag level (rather than as positional args) lets future commands
 * be added without breaking call sites. */
export interface PaletteActions {
  /** Switch active tab to Visual / Report / Explore. */
  setActiveTab: (tab: 'visual' | 'report' | 'explore') => void;
  /** Trigger the Run-Solver path from the palette. */
  runSolverFromPalette: () => void;
  /** Pick a material from the FALLBACK_MATERIALS list (by index). */
  pickMaterialByIndex: (index: number) => void;
  /** Scroll the material picker panel anchor into view. */
  openMaterialPickerPanel: () => void;
  /** Close the command palette. */
  closePalette: () => void;
  /** Active case id (used for the run-solver description hint). */
  activeCaseId: string | null;
  /** Material list. The palette emits one command per material in the
   * FALLBACK_MATERIALS table (currently 3 entries; extending the table
   * here automatically extends the palette). */
  materials: readonly MaterialRecord[];
}

/** Build the Cmd-K palette command list. The order is the order they
 * appear in the palette — preserve unless an explicit reordering is
 * being shipped. */
export function buildPaletteCommands(actions: PaletteActions): Command[] {
  const commands: Command[] = [
    {
      id: 'cmd-switch-tab-visual',
      label: 'Switch to 3D Scene tab',
      hotkey: 'g 1',
      category: 'navigation' as CommandCategory,
      handler: () => actions.setActiveTab('visual'),
    },
    {
      id: 'cmd-switch-tab-narrative',
      label: 'Switch to Narrative tab',
      hotkey: 'g 2',
      category: 'navigation' as CommandCategory,
      handler: () => actions.setActiveTab('report'),
    },
    {
      id: 'cmd-switch-tab-exploration',
      label: 'Switch to Exploration tab',
      hotkey: 'g 3',
      category: 'navigation' as CommandCategory,
      handler: () => actions.setActiveTab('explore'),
    },
    {
      id: 'cmd-run-solver',
      label: 'Run CalculiX solver on active case',
      description: actions.activeCaseId
        ? `Active case: ${actions.activeCaseId}`
        : 'No case selected — pick one first',
      category: 'solver' as CommandCategory,
      handler: actions.runSolverFromPalette,
    },
  ];
  // One command per FALLBACK_MATERIALS entry. Phase 22 D's
  // cmd-material-picker-open path (A:-2 anti-gaming) is preserved as
  // the LAST material command so the picker panel anchor lookup
  // always resolves after the inline picks.
  for (let i = 0; i < actions.materials.length; i++) {
    const m = actions.materials[i];
    commands.push({
      id: `cmd-pick-material-${m.id}`,
      label: `Pick material — ${m.name}`,
      category: 'material' as CommandCategory,
      handler: () => actions.pickMaterialByIndex(i),
    });
  }
  commands.push(
    {
      id: 'cmd-material-picker-open',
      label: 'Open material picker panel',
      category: 'material' as CommandCategory,
      handler: actions.openMaterialPickerPanel,
    },
    {
      id: 'cmd-close-palette',
      label: 'Close command palette',
      hotkey: 'escape',
      category: 'navigation' as CommandCategory,
      handler: actions.closePalette,
    },
  );
  return commands;
}

/** Pure-function builder for the Topbar's `materialOptions` prop
 * shape. Maps a MaterialRecord list to `{id, label}` view-model
 * entries. Kept here next to buildPaletteCommands because both are
 * topbar/palette configuration concerns. */
export function buildTopbarMaterialOptions(
  materials: readonly MaterialRecord[],
): { id: string; label: string }[] {
  return materials.map((m) => ({ id: m.id, label: m.name }));
}

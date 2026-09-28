<script lang="ts">
  import type { MenuButton } from "$lib/menu/model";
  import { ui } from "$lib/stores.svelte";
  import TaskFilters from "./TaskFilters.svelte";
  import TaskVariantRenderer from "./TaskVariantRenderer.svelte";

  interface Props {
    buttons: MenuButton[];
    disableActions: boolean;
    categories: string[];
  }

  let { buttons, disableActions, categories }: Props = $props();

  let query = $state("");

  // A running task stays visible even if hidden, so it can still be stopped.
  const isVisible = (b: MenuButton) =>
    ui.showHiddenTasks || b.isProcessRunning || !ui.isTaskHidden(b.taskKey);

  const hiddenCount = $derived(
    buttons.filter((b) => ui.isTaskHidden(b.taskKey)).length,
  );

  const filteredButtons = $derived(
    buttons.filter(
      (b) =>
        isVisible(b) &&
        b.option.label.toLowerCase().includes(query.toLowerCase()),
    ),
  );

  const categorizedButtons = $derived.by(() => {
    const result: Record<string, MenuButton[]> = {};
    for (const button of filteredButtons) {
      const category = button.option.category || "";
      if (!result[category]) {
        result[category] = [];
      }
      result[category].push(button);
    }
    return result;
  });

  const activeCategories = $derived.by(() => {
    const cats = categories.filter(
      (cat) => categorizedButtons[cat]?.length > 0,
    );
    if (categorizedButtons[""]?.length > 0 && !cats.includes("")) {
      cats.push("");
    }
    return cats;
  });
</script>

<div class="task-grid-container">
  <TaskFilters bind:query {hiddenCount} />
  <TaskVariantRenderer
    {activeCategories}
    {categorizedButtons}
    {disableActions}
  />
</div>

<style>
  .task-grid-container {
    display: flex;
    flex-direction: column;
    gap: 18px;
    height: 100%;
  }
</style>

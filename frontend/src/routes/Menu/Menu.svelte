<script lang="ts">
  import { Accordion } from "@skeletonlabs/skeleton-svelte";

  import type { MenuButton } from "$lib/model";
  import TooltipButton from "./TooltipButton.svelte";

  let {
    buttons,
    disableActions,
    categories,
  }: {
    buttons: MenuButton[];
    disableActions: boolean;
    categories: string[];
  } = $props();

  const categorizedButtons = $derived.by(() => {
    const result: Record<string, MenuButton[]> = {};

    for (const button of buttons) {
      const category = button.option.category || "";
      if (!result[category]) {
        result[category] = [];
      }
      result[category].push(button);
    }

    return result;
  });

  const uncategorizedButtons = $derived.by(() => {
    return categorizedButtons[""] || [];
  });
</script>

<div class="h-full max-h-full overflow-y-auto">
  {#if categories.length > 0}
    <Accordion multiple>
      {#each categories as category}
        {#if categorizedButtons[category] && categorizedButtons[category].length > 0}
          <Accordion.Item value={category}>
            {#snippet control()}<span class="h5">{category}</span>{/snippet}
            {#snippet panel()}
              <div class="flex flex-wrap justify-center gap-4">
                {#each categorizedButtons[category] as menuButton}
                  <TooltipButton {menuButton} {disableActions} />
                {/each}
              </div>
            {/snippet}
          </Accordion.Item>
          <hr class="hr" />
        {/if}
      {/each}
    </Accordion>
  {/if}

  {#if uncategorizedButtons.length > 0}
    <div class="mt-4 flex flex-wrap justify-center gap-4">
      {#each uncategorizedButtons as menuButton}
        <TooltipButton {menuButton} {disableActions} />
      {/each}
    </div>
  {/if}
</div>

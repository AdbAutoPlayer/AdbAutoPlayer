<script lang="ts">
  import { Tooltip } from "@skeletonlabs/skeleton-svelte";

  import ActionButton from "./ActionButton.svelte";
  import type { MenuButton } from "$lib/model";

  let openTooltip: string | null = $state(null);

  let {
    menuButton,
    disableActions,
  }: {
    menuButton: MenuButton;
    disableActions: boolean;
  } = $props();
  import { t } from "$lib/i18n/i18n";
</script>

{#if menuButton.option.tooltip}
  <Tooltip
    open={openTooltip === menuButton.option.label}
    onOpenChange={(e) => {
      if (e.open) {
        openTooltip = menuButton.option.label;
      } else if (openTooltip === menuButton.option.label) {
        openTooltip = null;
      }
    }}
    positioning={{ placement: "top" }}
    contentBase="card preset-filled-primary-500 p-4"
    openDelay={800}
    arrow
  >
    {#snippet trigger()}
      <ActionButton
        disabled={!menuButton.alwaysEnabled && disableActions}
        label={menuButton.option.label}
        isProcessRunning={menuButton.isProcessRunning}
        callback={menuButton.callback}
      ></ActionButton>
    {/snippet}
    {#snippet content()}
      <span class="select-none">
        {$t(menuButton.option.tooltip || "")}
      </span>
    {/snippet}
  </Tooltip>
{:else}
  <ActionButton
    disabled={!menuButton.alwaysEnabled && disableActions}
    label={menuButton.option.label}
    isProcessRunning={menuButton.isProcessRunning}
    callback={menuButton.callback}
  ></ActionButton>
{/if}

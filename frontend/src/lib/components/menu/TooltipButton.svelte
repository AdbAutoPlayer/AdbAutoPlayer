<script lang="ts">
  import { Portal, Tooltip } from "@skeletonlabs/skeleton-svelte";

  import ActionButton from "./ActionButton.svelte";
  import type { MenuButton } from "$lib/settings-form/model";

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
    openDelay={500}
    closeDelay={0}
  >
    <Tooltip.Trigger>
      <ActionButton
        disabled={!menuButton.alwaysEnabled && disableActions}
        {menuButton}
      />
    </Tooltip.Trigger>
    <Portal>
      <Tooltip.Positioner>
        <Tooltip.Content class="card preset-filled-primary-500 p-4 select-none">
          {$t(menuButton.option.tooltip || "")}
        </Tooltip.Content>
      </Tooltip.Positioner>
    </Portal>
  </Tooltip>
{:else}
  <ActionButton
    disabled={!menuButton.alwaysEnabled && disableActions}
    {menuButton}
  ></ActionButton>
{/if}

<script lang="ts">
  let {
    buttons,
    defaultButtons,
    disableActions,
  }: {
    buttons: MenuButton[];
    defaultButtons: MenuButton[];
    disableActions: boolean;
  } = $props();
  // https://next.skeleton.dev/docs/components/accordion/svelte#multiple
</script>

<div class="space-y-4">
  <div class="flex items-center gap-4">
    <!-- //TODO:: buttons is dynamic I cannot know how many buttons there will be I want it to automatically place buttons in a new row instead of scroll right  -->
    {#if buttons.length > 0}
      {#each buttons as { label, callback, active, alwaysEnabled }}
        <button
          type="button"
          disabled={!alwaysEnabled && disableActions}
          class:active
          class="btn preset-filled-primary-500"
          onclick={callback}
        >
          {label}
        </button>
      {/each}
    {:else}
      {#each defaultButtons as { label, callback, active, alwaysEnabled }}
        <button
          type="button"
          disabled={!alwaysEnabled && disableActions}
          class:active
          class="btn preset-filled-primary-500"
          onclick={callback}
        >
          {label}
        </button>
      {/each}
    {/if}
  </div>
</div>

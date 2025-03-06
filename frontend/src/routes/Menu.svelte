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
  <div class="flex flex-wrap justify-center gap-4">
    {#if buttons.length > 0}
      {#each buttons as { label, callback, active, alwaysEnabled }}
        <button
          type="button"
          disabled={!alwaysEnabled && disableActions}
          class="btn w-auto max-w-[200px]"
          class:preset-filled-primary-500={!active}
          class:hover:preset-filled-primary-700-300={!active}
          class:preset-outlined-primary-500={active}
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
          class="btn w-auto max-w-[200px]"
          class:preset-filled-primary-500={!active}
          class:hover:preset-filled-primary-700-300={!active}
          class:preset-outlined-primary-500={active}
          onclick={callback}
        >
          {label}
        </button>
      {/each}
    {/if}
  </div>
</div>

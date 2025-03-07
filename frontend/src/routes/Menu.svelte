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

<div class="h-full max-h-full overflow-y-auto">
  <h2 class="h2 text-2xl text-center pb-2">Menu</h2>

  <div class="flex flex-wrap justify-center gap-4">
    {#if buttons.length > 0}
      {#each buttons as { label, callback, active, alwaysEnabled }}
        <button
          type="button"
          disabled={!alwaysEnabled && disableActions}
          class="btn w-auto max-w-[200px]"
          class:preset-filled-primary-100-900={!active}
          class:hover:preset-filled-primary-500={!active}
          class:preset-outlined-primary-100-900={active}
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
          class:preset-filled-primary-100-900={!active}
          class:hover:preset-filled-primary-500={!active}
          class:preset-outlined-primary-100-900={active}
          onclick={callback}
        >
          {label}
        </button>
      {/each}
    {/if}
  </div>
</div>

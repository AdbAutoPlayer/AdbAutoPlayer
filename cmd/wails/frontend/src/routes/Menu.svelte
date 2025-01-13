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
</script>

{#if buttons.length > 0}
  {#each buttons as { label, callback, active, alwaysEnabled }}
    <button
      disabled={!alwaysEnabled && disableActions}
      class:active
      onclick={callback}
    >
      {label}
    </button>
  {/each}
{:else}
  {#each defaultButtons as { label, callback, active, alwaysEnabled }}
    <button
      disabled={!alwaysEnabled && disableActions}
      class:active
      onclick={callback}
    >
      {label}
    </button>
  {/each}
{/if}

<style>
  button {
    margin: 5px;
    padding: 10px 20px;
    font-size: 1em;
    cursor: pointer;
    border-radius: 5px;
    transition: background-color 0.2s ease-in-out;
  }

  button:disabled.active {
    opacity: 1;
    outline: 2px solid #396cd8;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
</style>

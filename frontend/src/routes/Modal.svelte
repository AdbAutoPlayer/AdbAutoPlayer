<script lang="ts">
  let { showModal = $bindable(), header, children, footer } = $props();

  let dialog: HTMLDialogElement | undefined = $state();

  $effect(() => {
    if (showModal) dialog?.showModal();
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog
  bind:this={dialog}
  onclose={() => (showModal = false)}
  onclick={(e) => {
    if (e.target === dialog) dialog.close();
  }}
>
  <div class="clearfix">
    {@render header?.()}
    <hr class="p-2" />
    {@render children?.()}
    <hr class="p-2" />
    <div class="flex justify-between w-full">
      {#if footer}
        {@render footer()}
      {/if}
      <button
        class="btn preset-filled-primary-500 hover:preset-filled-primary-700-300"
        onclick={() => dialog?.close()}
      >
        Close
      </button>
    </div>
  </div>
</dialog>

<style>
  dialog {
    max-width: 32em;
    border-radius: 0.2em;
    border: none;
    padding: 0;
    background-color: rgba(31, 31, 31, 1);
    margin: 10vh auto;
    position: fixed;
    left: 50%;
    transform: translateX(-50%);
    max-height: 80vh;
  }

  dialog > div {
    padding: 0;
    display: flex;
    flex-direction: column;
    max-height: 100%;
  }

  /* Style for the header */
  dialog > div > :first-child {
    padding: 1em;
    background-color: rgba(31, 31, 31, 1);
    position: sticky;
    top: 0;
    z-index: 10;
  }

  /* Style for the content area */
  dialog > div > :nth-child(3) {
    padding: 1em;
    overflow-y: auto;
    flex: 1;
  }

  /* Style for the footer */
  dialog > div > :last-child {
    padding: 1em;
    background-color: rgba(31, 31, 31, 1);
    position: sticky;
    bottom: 0;
    z-index: 10;
  }

  dialog::backdrop {
    background: rgba(0, 0, 0, 0.7);
  }
  dialog[open] {
    animation: zoom 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  }
  @keyframes zoom {
    from {
      transform: scale(0.95);
    }
    to {
      transform: scale(1);
    }
  }
  dialog[open]::backdrop {
    animation: fade 0.2s ease-out;
  }
  @keyframes fade {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  .clearfix::after {
    content: "";
    display: table;
    clear: both;
  }
</style>

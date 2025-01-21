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
    <hr />
    {@render children?.()}
    <hr />
    {#if footer}
      {@render footer()}
      <!-- svelte-ignore a11y_autofocus -->
      <button class="closeWithFooter" autofocus onclick={() => dialog?.close()}>
        Close
      </button>
    {:else}
      <!-- svelte-ignore a11y_autofocus -->
      <button class="closeNoFooter" autofocus onclick={() => dialog?.close()}>
        Close
      </button>
    {/if}
  </div>
</dialog>

<style>
  .closeWithFooter {
    float: right;
  }
  .closeNoFooter {
    display: inline-block;
    margin-left: auto;
    margin-right: 0;
  }
  dialog {
    max-width: 32em;
    border-radius: 0.2em;
    border: none;
    padding: 0;
    background-color: rgba(31, 31, 31, 1);
  }
  dialog::backdrop {
    background: rgba(0, 0, 0, 0.7);
  }
  dialog > div {
    padding: 1em;
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

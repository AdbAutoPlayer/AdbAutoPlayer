<script lang="ts">
  interface Props {
    show: boolean;
    onClick: () => void;
  }

  let { show, onClick }: Props = $props();
</script>

{#if show}
  <button
    onclick={onClick}
    class="fixed top-0 right-0 z-50 m-2 cursor-pointer rounded-full bg-primary-500 p-2 shadow-lg transition-colors select-none hover:bg-primary-600"
    draggable="false"
    title="Update Available"
  >
    <img
      src="/icons/download-cloud.svg"
      alt="Download"
      width="24"
      height="24"
      draggable="false"
    />
  </button>
{/if}

<script lang="ts">
  import IconDownloadCloud from "$lib/components/icons/feather/IconDownloadCloud.svelte";

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
    <IconDownloadCloud size={24} strokeWidth={2} />
  </button>
{/if}

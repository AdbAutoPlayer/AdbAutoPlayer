<script lang="ts">
  import FileDropZone from "$lib/components/generic/FileDropZone.svelte";
</script>

<h1 class="pb-2 text-center h1 text-3xl select-none">Log Reader</h1>
<div
  class="flex max-h-[70vh] min-h-[20vh] flex-col overflow-hidden card bg-surface-100-900/50 p-4 text-center select-none"
>
  <FileDropZone message="Drop .log file here" />
</div>

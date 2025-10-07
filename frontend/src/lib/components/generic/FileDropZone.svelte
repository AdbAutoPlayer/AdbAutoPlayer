<script lang="ts">
  import FilePlus from "$lib/components/icons/lucide/FilePlus.svelte";

  let { message } = $props();
</script>

<div
  class="mx-auto flex w-full flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed p-8 text-center text-surface-700 hover:border-surface-900"
  data-wails-dropzone
>
  <FilePlus size={48} />
  <p class="text-lg font-medium" data-wails-dropzone>
    {message}
  </p>
</div>

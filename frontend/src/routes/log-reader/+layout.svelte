<script lang="ts">
  import DocumentationIconSticky from "$lib/components/sticky/DocumentationIconSticky.svelte";
  import LogoSticky from "$lib/components/sticky/LogoSticky.svelte";
  import LogReaderDisplayCard from "$lib/components/log/LogReaderDisplayCard.svelte";

  let { children } = $props();
</script>

<div class="flex h-screen flex-col overflow-hidden">
  <div class="flex-none">
    <DocumentationIconSticky />
    <LogoSticky />
  </div>
  <main class="w-full pt-2 pr-4 pb-4 pl-4">
    {@render children()}
  </main>
  <LogReaderDisplayCard />
</div>

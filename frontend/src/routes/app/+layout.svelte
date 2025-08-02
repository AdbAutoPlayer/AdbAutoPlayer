<script lang="ts">
  import LogoSticky from "$lib/components/sticky/LogoSticky.svelte";
  import DocumentationIconSticky from "$lib/components/sticky/DocumentationIconSticky.svelte";
  import LogDisplayCard from "$lib/components/log/LogDisplayCard.svelte";
  import { onMount } from "svelte";
  import UpdateContainer from "$lib/components/updater/UpdateContainer.svelte";
  import { Toaster } from "@skeletonlabs/skeleton-svelte";
  import { toaster } from "$lib/toast/toaster-svelte";
  import { registerGlobalHotkeys } from "$lib/utils/settings";
  import { initPostHog } from "$lib/utils/posthog";

  let { children } = $props();

  onMount(() => {
    initPostHog();
    registerGlobalHotkeys();
  });
</script>

<Toaster {toaster} stateError="preset-filled-error-100-900"></Toaster>

<div class="flex h-screen flex-col overflow-hidden">
  <div class="flex-none">
    <DocumentationIconSticky />
    <UpdateContainer />
    <LogoSticky />
  </div>
  <main class="w-full pt-2 pr-4 pb-4 pl-4">
    {@render children()}
  </main>
  <LogDisplayCard />
</div>

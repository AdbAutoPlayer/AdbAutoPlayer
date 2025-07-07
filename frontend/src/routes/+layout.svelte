<script lang="ts">
  import "../app.css";

  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import LogDisplayCard from "./Log/LogDisplayCard.svelte";
  import { onMount } from "svelte";
  import UpdateContainer from "./Updater/UpdateContainer.svelte";
  import { Toaster } from "@skeletonlabs/skeleton-svelte";
  import { toaster } from "$lib/utils/toaster-svelte";
  import {
    applyUISettingsFromFile,
    registerGlobalHotkeys,
  } from "$lib/utils/settings";
  import { initPostHog } from "$lib/utils/posthog";
  import { setupExternalLinkHandler } from "$lib/utils/external-links";

  let { children } = $props();

  onMount(() => {
    initPostHog();
    applyUISettingsFromFile();
    registerGlobalHotkeys();

    return setupExternalLinkHandler();
  });
</script>

<Toaster {toaster} stateError="preset-filled-error-100-900"></Toaster>

<div class="flex h-screen flex-col overflow-hidden">
  <div class="flex-none">
    <DocumentationIconSticky />
    <UpdateContainer />
    <LogoSticky />
  </div>
  <main class="w-full p-4">
    {@render children()}
  </main>
  <LogDisplayCard />
</div>

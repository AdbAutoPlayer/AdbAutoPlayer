<script lang="ts">
  import "../app.css";

  import { onMount } from "svelte";
  import { setupExternalLinkHandler } from "$lib/utils/external-links";
  import { applySettingsFromFile } from "$lib/utils/settings";
  import { invoke } from "@tauri-apps/api/core";
  import { toaster } from "$lib/toast/toaster-svelte";
  import DocumentationIconSticky from "$lib/components/sticky/DocumentationIconSticky.svelte";
  import LogoSticky from "$lib/components/sticky/LogoSticky.svelte";
  import { Toast } from "@skeletonlabs/skeleton-svelte";
  import { initPostHog } from "$lib/utils/posthog";
  import { logInfo } from "$lib/log/log-events";
  import { getVersion } from "@tauri-apps/api/app";

  let { children } = $props();

  async function init() {
    await applySettingsFromFile();
    // Show Window after load to prevent getting flash banged at night.
    await invoke("show_window");

    const version = await getVersion();
    console.log(version);
    await logInfo(`App Version: ${version}`);
  }

  init()

  onMount(() => {
    return setupExternalLinkHandler();
  });

  onMount(() => {
    initPostHog();
  });
</script>


<Toast.Group {toaster}>
  {#snippet children(toast)}
    <Toast {toast} class="data-[type=error]:preset-filled-error-100-900">
      <Toast.Message>
        <Toast.Title>
          <span class="text-lg">{toast.title}</span>
        </Toast.Title>
        <Toast.Description>
          <p>{toast.description}</p>
        </Toast.Description>
      </Toast.Message>
      <Toast.CloseTrigger />
    </Toast>
  {/snippet}
</Toast.Group>

<div class="flex h-screen flex-col overflow-hidden">
  <header class="flex-none">
    <DocumentationIconSticky />
    <LogoSticky />
  </header>

  {@render children()}
</div>

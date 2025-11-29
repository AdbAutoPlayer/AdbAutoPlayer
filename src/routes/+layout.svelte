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
  import { profileStates, profileStateTimestamp } from "$lib/stores";
  import { listen } from "@tauri-apps/api/event";
  import { EventNames } from "$lib/log/eventNames";
  import type { ProfileStateUpdate } from "$pytauri/_apiTypes";

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
    let unsubscribers: Array<() => void> = [];

    const setupListeners = async () => {
      const stateUnsub = await listen<ProfileStateUpdate>(
        EventNames.PROFILE_STATE_UPDATE,
        (event) => {
          // Prevent race condition with optimistic UI updates.
          if ($profileStateTimestamp && $profileStateTimestamp >= event.payload.timestamp) {
            return;
          }
          $profileStates[event.payload.index] = {
            game_menu: event.payload.state.game_menu,
            active_task: event.payload.state.active_task,
            device_id: event.payload.state.device_id,
          }
        }
      );

      unsubscribers.push(stateUnsub);
    };

    setupListeners();
    return () => unsubscribers.forEach((unsub) => unsub());
  })

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

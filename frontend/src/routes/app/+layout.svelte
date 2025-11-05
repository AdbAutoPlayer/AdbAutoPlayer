<script lang="ts">
  import LogoSticky from "$lib/components/sticky/LogoSticky.svelte";
  import DocumentationIconSticky from "$lib/components/sticky/DocumentationIconSticky.svelte";
  import ActiveLogDisplayCard from "$lib/components/log/ActiveLogDisplayCard.svelte";
  import { onMount } from "svelte";
  import UpdateContainer from "$lib/components/updater/UpdateContainer.svelte";
  import { Toast } from "@skeletonlabs/skeleton-svelte";
  import { toaster } from "$lib/toast/toaster-svelte";
  import { registerGlobalHotkeys } from "$lib/utils/settings";
  import { initPostHog } from "$lib/utils/posthog";

  let { children } = $props();

  onMount(() => {
    initPostHog();
    registerGlobalHotkeys();
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
  <div class="flex-none">
    <DocumentationIconSticky />
    <UpdateContainer />
    <LogoSticky />
  </div>
  <main class="w-full pt-2 pr-4 pb-4 pl-4">
    {@render children()}
  </main>
  <ActiveLogDisplayCard />
</div>

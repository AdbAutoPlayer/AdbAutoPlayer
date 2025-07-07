<script lang="ts">
  import "../app.css";

  import { BrowserOpenURL } from "$lib/wailsjs/runtime";
  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import LogDisplayCard from "./Log/LogDisplayCard.svelte";
  import { onMount } from "svelte";
  import posthog from "posthog-js";
  import { browser } from "$app/environment";
  import { version } from "$app/environment";
  import UpdateContainer from "./Updater/UpdateContainer.svelte";
  import { Toaster } from "@skeletonlabs/skeleton-svelte";
  import { toaster } from "$lib/utils/toaster-svelte";
  import {
    applyUISettingsFromFile,
    registerGlobalHotkeys,
  } from "$lib/utils/settings";

  let { children } = $props();

  const POSTHOG_KEY = "phc_GXmHn56fL10ymOt3inmqSER4wh5YuN3AG6lmauJ5b0o";
  const POSTHOG_HOST = "https://eu.i.posthog.com";

  function shouldOpenExternally(url: string): boolean {
    if (!url) {
      return false;
    }
    if (url.startsWith("#") || url.startsWith("/")) {
      return false;
    }

    if (url.startsWith("http://wails.localhost")) {
      return false;
    }

    if (url.startsWith("file://")) {
      return false;
    }

    return url.includes("://");
  }

  function initPostHog() {
    if (!browser) {
      return;
    }

    try {
      posthog.init(POSTHOG_KEY, {
        api_host: POSTHOG_HOST,
        autocapture: {
          css_selector_allowlist: [".ph-autocapture"],
        },
        person_profiles: "always",
      });

      posthog.register({
        app_version: version as string,
      });
    } catch (error) {
      console.error("Failed to initialize PostHog:", error);
    }
  }

  onMount(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const anchor = target.closest("a");

      if (!(anchor instanceof HTMLAnchorElement)) {
        return;
      }

      const url = anchor.href;

      if (shouldOpenExternally(url)) {
        e.preventDefault();
        BrowserOpenURL(url);
      }
    };

    initPostHog();
    applyUISettingsFromFile();
    registerGlobalHotkeys();

    document.body.addEventListener("click", handleClick);

    return () => {
      document.body.removeEventListener("click", handleClick);
    };
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

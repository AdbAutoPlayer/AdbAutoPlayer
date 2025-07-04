<script lang="ts">
  import "../app.css";

  import { BrowserOpenURL, EventsOn } from "$lib/wailsjs/runtime";
  import { GetTheme, RegisterGlobalHotkeys } from "$lib/wailsjs/go/main/App";
  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import LogDisplayCard from "./Log/LogDisplayCard.svelte";
  import { LogError } from "$lib/wailsjs/runtime";
  import { onMount } from "svelte";
  import posthog from "posthog-js";
  import { browser } from "$app/environment";
  import { version } from "$app/environment";
  import UpdateContainer from "./Updater/UpdateContainer.svelte";
  import { Toaster } from "@skeletonlabs/skeleton-svelte";
  import { toaster } from "$lib/utils/toaster-svelte";
  import { showErrorToast } from "$lib/utils/error";

  let { children } = $props();

  const POSTHOG_KEY = "phc_GXmHn56fL10ymOt3inmqSER4wh5YuN3AG6lmauJ5b0o";
  const POSTHOG_HOST = "https://eu.i.posthog.com";
  const DEFAULT_THEME = "catppuccin";

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

  function loadTheme() {
    GetTheme()
      .then((theme) => {
        console.log("Selected theme:", theme);
        document.documentElement.setAttribute("data-theme", theme);
      })
      .catch((error) => {
        LogError(`Failed to load theme: ${error}`);
        document.documentElement.setAttribute("data-theme", DEFAULT_THEME);
      });
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
    loadTheme();

    document.body.addEventListener("click", handleClick);

    return () => {
      document.body.removeEventListener("click", handleClick);
    };
  });

  EventsOn("failed-to-register-global-stop-hotkey", (error: string) => {
    showErrorToast(error, {
      title: "Failed to register Global Stop HotKey",
    });
  });
  RegisterGlobalHotkeys();
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

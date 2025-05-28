<script lang="ts">
  import "../app.css";

  import { BrowserOpenURL } from "$lib/wailsjs/runtime";
  import { GetTheme } from "$lib/wailsjs/go/main/App";
  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import DownloadIconSticky from "./Updater/DownloadIconSticky.svelte";
  import LogDisplayCard from "./LogDisplayCard.svelte";
  import { onMount } from "svelte";
  import posthog from "posthog-js";
  import { browser } from "$app/environment";
  import { version } from "$app/environment";

  let { children } = $props();

  document.body.addEventListener("click", function (e: MouseEvent) {
    const target = e.target as HTMLElement;

    const anchor = target.closest("a");

    if (!(anchor instanceof HTMLAnchorElement)) {
      return;
    }
    const url = anchor.href;
    if (
      !url.startsWith("http://#") &&
      !url.startsWith("file://") &&
      !url.startsWith("http://wails.localhost:")
    ) {
      e.preventDefault();
      BrowserOpenURL(url);
    }
  });

  onMount(async () => {
    const theme = await GetTheme();
    // Now apply theme via a <link> tag, class, or dynamically import the CSS
    console.log("Selected theme:", theme);
    document.documentElement.setAttribute("data-theme", theme);
  });

  onMount(() => {
    if (browser) {
      // this is going to be exposed in the frontend anyway.
      posthog.init("phc_GXmHn56fL10ymOt3inmqSER4wh5YuN3AG6lmauJ5b0o", {
        api_host: "https://eu.i.posthog.com",
        autocapture: {
          css_selector_allowlist: [".ph-autocapture"],
        },
        person_profiles: "always",
      });
    }

    posthog.register({
      app_version: version,
    });
  });
</script>

<div class="flex h-screen flex-col overflow-hidden">
  <div class="flex-none">
    <DocumentationIconSticky></DocumentationIconSticky>
    <DownloadIconSticky></DownloadIconSticky>
    <LogoSticky></LogoSticky>
  </div>
  <main class="w-full p-4">
    {@render children()}
  </main>
  <LogDisplayCard />
</div>

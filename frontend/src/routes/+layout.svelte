<script lang="ts">
  import "../app.css";

  import { BrowserOpenURL } from "$lib/wailsjs/runtime";
  import { GetTheme } from "$lib/wailsjs/go/main/App";
  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import DownloadIconSticky from "./SelfUpdater/DownloadIconSticky.svelte";
  import LogDisplayCard from "./LogDisplayCard.svelte";
  import { onMount } from "svelte";

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

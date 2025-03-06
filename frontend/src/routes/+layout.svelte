<script lang="ts">
  import "../app.css";

  import { BrowserOpenURL } from "$lib/wailsjs/runtime";

  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import DownloadIconSticky from "./DownloadIconSticky.svelte";
  import LogDisplayCard from "./LogDisplayCard.svelte";

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
</script>

<div class="flex flex-col h-screen overflow-hidden">
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

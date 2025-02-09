<script lang="ts">
  import "../app.css";

  import { BrowserOpenURL } from "$lib/wailsjs/runtime";

  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import DownloadIconSticky from "./DownloadIconSticky.svelte";
  import CommandPanel from "./CommandPanel.svelte";
  import LogDisplay from "./LogDisplay.svelte";

  let { children } = $props();

  document.body.addEventListener("click", function (e: MouseEvent) {
    e.preventDefault();
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

<DocumentationIconSticky></DocumentationIconSticky>
<DownloadIconSticky></DownloadIconSticky>
<LogoSticky></LogoSticky>

{@render children()}

<CommandPanel title={"Logs"}>
  <LogDisplay />
</CommandPanel>

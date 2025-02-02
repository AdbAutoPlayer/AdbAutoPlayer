<script lang="ts">
  import "../app.css";

  import LogoSticky from "./LogoSticky.svelte";
  import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
  import DownloadIconSticky from "./DownloadIconSticky.svelte";
  import CommandPanel from "./CommandPanel.svelte";
  import LogDisplay from "./LogDisplay.svelte";

  let { children } = $props();
</script>

<DocumentationIconSticky></DocumentationIconSticky>
<DownloadIconSticky></DownloadIconSticky>
<LogoSticky></LogoSticky>

{@render children()}

<CommandPanel title={"Logs"}>
  <LogDisplay />
</CommandPanel>

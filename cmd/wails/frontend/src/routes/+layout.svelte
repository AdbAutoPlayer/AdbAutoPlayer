<script lang="ts">
    import LogoSticky from "./LogoSticky.svelte";
    import DocumentationIconSticky from "./DocumentationIconSticky.svelte";
    import DownloadIconSticky from "./DownloadIconSticky.svelte";

    let { children } = $props();
</script>

<DocumentationIconSticky></DocumentationIconSticky>
<DownloadIconSticky></DownloadIconSticky>
<LogoSticky></LogoSticky>

{@render children()}

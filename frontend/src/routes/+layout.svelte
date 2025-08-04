<script lang="ts">
  import "../app.css";

  import { onMount } from "svelte";
  import {
    applyUISettings,
    applyUISettingsFromFile,
  } from "$lib/utils/settings";
  import { setupExternalLinkHandler } from "$lib/utils/external-links";
  import { Events } from "@wailsio/runtime";
  import { EventNames } from "$lib/log/eventNames";
  import { GeneralSettings } from "@wails/settings";

  let { children } = $props();

  onMount(() => {
    applyUISettingsFromFile();

    const unsubscribe = Events.On(EventNames.GENERAL_SETTINGS_UPDATED, (ev) => {
      const generalSettings = ev.data as GeneralSettings;
      applyUISettings(generalSettings["User Interface"]);
    });

    return () => {
      unsubscribe();
    };
  });

  onMount(() => {
    return setupExternalLinkHandler();
  });
</script>

{@render children()}

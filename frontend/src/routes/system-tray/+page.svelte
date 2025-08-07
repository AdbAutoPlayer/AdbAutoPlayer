<script lang="ts">
  import { Events } from "@wailsio/runtime";
  import { EventNames } from "$lib/log/eventNames";
  import {
    MinimizeToTray,
    ShowWindow,
    Exit,
  } from "@wails/system_tray/systemtrayservice";
  import { onMount } from "svelte";

  let windowIsVisible = $state(true);

  onMount(() => {
    const unsubscribe = Events.On(EventNames.WINDOW_IS_VISIBLE, (ev) => {
      windowIsVisible = ev.data;
    });

    return () => {
      unsubscribe();
    };
  });
</script>

<div
  class="flex min-h-screen w-full max-w-md flex-col items-center justify-center"
>
  {#if windowIsVisible}
    <div class="flex w-full flex-row">
      <button onclick={MinimizeToTray} class="variant-filled btn w-full">
        Minimize to Tray
      </button>
    </div>
  {:else}
    <div class="flex w-full flex-row">
      <button onclick={ShowWindow} class="variant-filled btn w-full">
        Show AdbAutoPlayer
      </button>
    </div>
  {/if}
  <hr class="hr" />
  <div class="flex w-full flex-row">
    <button onclick={Exit} class="variant-filled btn w-full"> Exit </button>
  </div>
</div>

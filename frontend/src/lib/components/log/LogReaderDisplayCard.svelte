<script lang="ts">
  import TextDisplayCard from "$lib/components/generic/TextDisplayCard.svelte";
  import { logMessageToTextDisplayCardItem } from "$lib/log/logHelper";
  import { onMount } from "svelte";
  import { Events } from "@wailsio/runtime";
  import { EventNames } from "$lib/log/eventNames";

  let textDisplayCard: TextDisplayCard;

  interface LogReaderMessageEvent {
    data: LogMessage | LogMessage[];
  }

  onMount(() => {
    const unsubscribers = [
      Events.On(EventNames.LOG_READER_MESSAGE, (ev: LogReaderMessageEvent) => {
        const messages = Array.isArray(ev.data) ? ev.data : [ev.data];

        for (const logMessage of messages) {
          textDisplayCard.appendEntry(
            logMessageToTextDisplayCardItem(logMessage, true),
          );
        }
      }),
      Events.On(EventNames.LOG_READER_CLEAR, () => {
        textDisplayCard.clear();
      }),
    ];

    return () => unsubscribers.forEach((unsub) => unsub());
  });
</script>

<TextDisplayCard
  bind:this={textDisplayCard}
  maxEntries={10000}
  enableSearch={true}
/>

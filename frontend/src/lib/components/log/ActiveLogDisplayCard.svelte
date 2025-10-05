<script lang="ts">
  import TextDisplayCard from "$lib/components/generic/TextDisplayCard.svelte";
  import { Events } from "@wailsio/runtime";
  import { EventNames } from "$lib/log/eventNames";
  import { Instant } from "@js-joda/core";
  import {
    formatMessage,
    logMessageToTextDisplayCardItem,
  } from "$lib/log/logHelper";
  import { onMount } from "svelte";

  let textDisplayCard: TextDisplayCard;

  function addSummaryMessageToLog(summary: { summary_message: string }) {
    const summaryMessage = formatMessage(summary.summary_message);
    if ("" === summaryMessage) {
      return;
    }
    textDisplayCard.appendEntry({
      message: summaryMessage,
      timestamp: Instant.now(),
      html_class: "whitespace-pre-wrap text-success-950",
    });
  }

  onMount(() => {
    const unsubscribers = [
      Events.On(EventNames.WRITE_SUMMARY_TO_LOG, (ev) => {
        const summary = ev.data;
        if (summary) addSummaryMessageToLog(summary);
      }),

      Events.On(EventNames.LOG_MESSAGE, (ev) => {
        const logMessage: LogMessage = ev.data;
        textDisplayCard.appendEntry(
          logMessageToTextDisplayCardItem(logMessage),
        );
      }),

      Events.On(EventNames.ADB_AUTO_PLAYER_SETTINGS_UPDATED, () => {
        textDisplayCard.slice(0, 1);
      }),
    ];

    return () => unsubscribers.forEach((unsub) => unsub());
  });
</script>

<TextDisplayCard bind:this={textDisplayCard} />

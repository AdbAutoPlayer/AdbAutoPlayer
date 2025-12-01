<script lang="ts">
  import TextDisplayCard from "$lib/components/generic/TextDisplayCard.svelte";
  import { EventNames } from "$lib/log/eventNames";
  import { Instant } from "@js-joda/core";
  import {
    formatMessage,
    logMessageToTextDisplayCardItem,
  } from "$lib/log/logHelper";
  import type { TextDisplayCardItem } from "$lib/log/logHelper";
  import { onMount } from "svelte";
  import { listen } from "@tauri-apps/api/event";
  import { appSettings, debugLogLevelOverwrite } from "$lib/stores";

  interface SummaryData {
    profile_index: number;
    msg: string | null;
  }

  interface Props {
    profileIndex?: number;
  }

  let { profileIndex = 0 }: Props = $props();

  let profileEntries: Record<number, TextDisplayCardItem[]> = $state({});
  let maxEntries = 1000;

  const logLevelOrder: Record<LogLevel, number> = {
    DEBUG: 0,
    INFO: 1,
    WARNING: 2,
    ERROR: 3,
    FATAL: 4,
  };

  function getOrCreateEntriesForProfile(index: number): TextDisplayCardItem[] {
    return profileEntries[index] ?? [];
  }

  function insertEntry(
    index: number | undefined | null,
    entry: TextDisplayCardItem,
  ) {
    const insertCount =
      index === undefined || index === null
        ? ($appSettings?.profiles?.profiles?.length ?? 1)
        : 1;

    const startIndex = index ?? 0;

    for (let i = 0; i < insertCount; i++) {
      const targetIndex = startIndex + i;

      profileEntries[targetIndex] ??= [];

      profileEntries[targetIndex].push(entry);

      if (profileEntries[targetIndex].length > maxEntries) {
        profileEntries[targetIndex].shift();
      }
    }
  }

  function addSummaryMessageToLog(summary: SummaryData) {
    if (!summary.msg) {
      return;
    }

    const summaryProfileIndex = summary.profile_index;
    const summaryMessage = formatMessage(summary.msg);
    if ("" === summaryMessage) {
      return;
    }

    insertEntry(summaryProfileIndex, {
      message: summaryMessage,
      timestamp: Instant.now(),
      html_class: "whitespace-pre-wrap text-success-950",
    });
  }

  onMount(() => {
    let unsubscribers: Array<() => void> = [];

    const setupListeners = async () => {
      const logUnsub = await listen<LogMessage>(
        EventNames.LOG_MESSAGE,
        (event) => {
          const logMessage = event.payload;
          const logLevel: LogLevel = $appSettings?.logging?.level ?? "INFO";

          if (
            $debugLogLevelOverwrite ||
            logLevelOrder[logMessage.level] >= logLevelOrder[logLevel]
          ) {
            insertEntry(
              logMessage.profile_index,
              logMessageToTextDisplayCardItem(logMessage),
            );
          }
        },
      );

      const summaryUnsub = await listen<SummaryData>(
        EventNames.WRITE_SUMMARY_TO_LOG,
        (event) => {
          if (event.payload) addSummaryMessageToLog(event.payload);
        },
      );

      unsubscribers.push(logUnsub, summaryUnsub);
    };

    setupListeners();
    return () => unsubscribers.forEach((unsub) => unsub());
  });

  let currentEntries = $derived(getOrCreateEntriesForProfile(profileIndex));
</script>

<TextDisplayCard entries={currentEntries} />

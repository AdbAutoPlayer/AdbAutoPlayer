<script lang="ts">
  import { t } from "$lib/i18n/i18n";
  import { onMount, tick } from "svelte";
  import { listen } from "@tauri-apps/api/event";
  import { revealItemInDir } from "@tauri-apps/plugin-opener";
  import { saveLogFile } from "$pytauri/apiClient";
  import { homeDir } from "@tauri-apps/api/path";
  import { profiles, settings, ui } from "$lib/stores.svelte";
  import { EventNames } from "$lib/log/eventNames";
  import {
    formatMessage,
    logMessageToTextDisplayCardItem,
  } from "$lib/log/logHelper";
  import type { TextDisplayCardItem } from "$lib/log/logHelper";
  import { Instant } from "@js-joda/core";
  import LogEntry from "./LogEntry.svelte";
  import LogFilters from "./LogFilters.svelte";
  import LogActions from "./LogActions.svelte";

  const awakeMascot = "/images/3583082.png";
  const sleepMascot = "/images/3583083.png";

  interface TaskCompletedEvent {
    profile_index: number;
    msg: string | null;
    exit_code: number | null;
  }

  interface Props {
    profileIndex: number;
    onClear: () => void;
    collapsed: boolean;
    position?: "right" | "bottom";
  }

  let {
    profileIndex,
    onClear,
    collapsed,
    position = "right",
  }: Props = $props();

  let profileEntries: Record<number, TextDisplayCardItem[]> = $state({});
  let maxEntries = 5000;
  let scrollContainer: HTMLDivElement | null = $state(null);

  const logLevelOrder: Record<string, number> = {
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
        ? (settings.settings?.profiles?.profiles?.length ?? 1)
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

    // Trigger reactivity for profileEntries
    profileEntries = { ...profileEntries };

    scrollToBottom();
  }

  async function scrollToBottom() {
    await tick();
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  }

  function addSummaryMessageToLog(summary: TaskCompletedEvent) {
    if (!summary.msg) return;
    const summaryProfileIndex = summary.profile_index;
    const summaryMessage = formatMessage(summary.msg);
    if ("" === summaryMessage) return;

    insertEntry(summaryProfileIndex, {
      message: summaryMessage,
      timestamp: Instant.now(),
      html_class: "whitespace-pre-wrap text-secondary-500",
      level: "INFO",
    } as any);
  }

  onMount(() => {
    let unsubscribers: Array<() => void> = [];
    const setupListeners = async () => {
      const logUnsub = await listen<any>(EventNames.LOG_MESSAGE, (event) => {
        const logMessage = event.payload;
        const configLogLevel =
          (settings.settings?.logging?.level as string) ?? "INFO";

        let alwaysLogDebug = false;
        if (logMessage.profile_index !== undefined) {
          alwaysLogDebug =
            settings.debugLogLevelOverwrite[logMessage.profile_index] ?? false;
        }

        if (
          alwaysLogDebug ||
          logLevelOrder[logMessage.level] >= logLevelOrder[configLogLevel]
        ) {
          const entry = logMessageToTextDisplayCardItem(logMessage);
          (entry as any).level = logMessage.level; // Keep level for styling
          insertEntry(logMessage.profile_index, entry);
        }
      });

      const summaryUnsub = await listen<TaskCompletedEvent>(
        EventNames.TASK_COMPLETED,
        (event) => {
          if (event.payload) addSummaryMessageToLog(event.payload);
        },
      );

      unsubscribers.push(logUnsub, summaryUnsub);
    };

    setupListeners();
    return () => unsubscribers.forEach((unsub) => unsub());
  });

  const currentEntries = $derived(getOrCreateEntriesForProfile(profileIndex));

  function handleClear() {
    profileEntries[profileIndex] = [];
    profileEntries = { ...profileEntries };
    onClear();
  }

  function fmtTime(instant: Instant) {
    const d = new Date(instant.toEpochMilli());
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
  }

  async function handleExport() {
    if (currentEntries.length === 0) return;
    const logText = currentEntries
      .map(
        (e) =>
          `[${fmtTime(e.timestamp)}] [${(e as any).level || "INFO"}] ${e.message.replace(/<[^>]*>/g, "")}`,
      )
      .join("\n");
    const filename = `adbautoplayer-log-profile-${profileIndex}-${new Date().toISOString().slice(0, 10)}.txt`;
    try {
      const savedPath = await saveLogFile({ content: logText, filename });
      await revealItemInDir(savedPath);
    } catch (e) {
      console.error("Failed to export log:", e);
    }
  }

  const isTaskRunning = $derived(!!profiles.states[profileIndex]?.active_task);

  async function handleLogClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    const pathLink = target.closest(".path-link");
    if (pathLink) {
      let path = pathLink.getAttribute("data-path");
      if (path) {
        // Expand environment variables
        if (path.includes("%USERPROFILE%")) {
          const home = await homeDir();
          path = path.replace("%USERPROFILE%", home);
        } else if (path.startsWith("~")) {
          const home = await homeDir();
          path = path.replace("~", home);
        }

        try {
          await revealItemInDir(path);
        } catch (e) {
          console.error("Failed to open path:", e);
        }
      }
    }
  }
</script>

<div
  class="log-panel"
  class:collapsed
  class:compact={ui.taskViewVariant === "accordion"}
  data-position={position}
>
  <div class="header">
    <LogFilters linesCount={currentEntries.length} />
    <LogActions onClear={handleClear} onExport={handleExport} />
  </div>

  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="scroll-area" bind:this={scrollContainer} onclick={handleLogClick}>
    <img
      src={isTaskRunning ? sleepMascot : awakeMascot}
      alt="mascot"
      class="mascot-watermark"
      draggable="false"
    />

    {#each currentEntries as entry}
      <LogEntry {entry} />
    {/each}
    {#if currentEntries.length === 0}
      <div class="empty">{$t("No logs for this profile yet...")}</div>
    {/if}
  </div>
</div>

<style>
  .log-panel {
    display: flex;
    flex-direction: column;
    background: var(--bg-1);
    min-width: 0;
    transition: all var(--dur-2) var(--ease);
  }

  .log-panel[data-position="right"] {
    width: 400px;
    flex: 0 0 400px;
    border-left: 1px solid var(--line);
    height: 100%;
  }

  .log-panel[data-position="right"].collapsed {
    width: 0;
    flex: 0 0 0;
    border-left: none;
    overflow: hidden;
  }

  .log-panel[data-position="bottom"] {
    height: 250px;
    flex: 0 0 250px;
    border-top: 1px solid var(--line);
    width: 100%;
  }

  .log-panel[data-position="bottom"].collapsed {
    height: 0;
    flex: 0 0 0;
    border-top: none;
    overflow: hidden;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--line);
  }

  .scroll-area {
    flex: 1;
    overflow: auto;
    padding: 8px 0;
    background: var(--log-bg);
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 1.55;
    position: relative;
  }

  .empty {
    padding: 20px;
    color: var(--text-4);
    text-align: center;
    font-style: italic;
  }

  /* Compact Mode Styles */
  .log-panel.compact[data-position="bottom"] {
    height: 160px;
    flex: 0 0 160px;
  }

  .log-panel.compact[data-position="bottom"] .header {
    padding: 6px 14px;
  }

  .log-panel.compact[data-position="bottom"] .scroll-area {
    font-size: 11.5px;
    line-height: 1.4;
  }

  .mascot-watermark {
    position: absolute;
    bottom: 0;
    right: 8px;
    width: 140px;
    height: auto;
    opacity: 0.15;
    pointer-events: none;
    user-select: none;
    z-index: 0; /* Behind the text */
    filter: grayscale(0.2);
    transition:
      opacity var(--dur-2),
      width var(--dur-2);
  }

  /* Lateral mode specific adjustments */
  .log-panel[data-position="right"] .mascot-watermark {
    width: 110px;
    right: 4px;
    opacity: 0.12;
  }

  .log-panel:hover .mascot-watermark {
    opacity: 0.25;
  }

  .log-panel.compact .mascot-watermark {
    width: 90px;
    right: 4px;
  }
</style>

<script lang="ts">
  import { EventsOn } from "$lib/wailsjs/runtime";
  import IconX from "../Icons/IconX.svelte";

  type LogEntry = {
    message: string;
    html_class: string;
  };

  let logs: LogEntry[] = $state([]);
  let summaryMessage: string = $state("");
  let searchTerm: string = $state("");
  let searchVisible: boolean = $state(false);
  let currentMatchIndex: number = $state(-1);
  let searchInput: HTMLInputElement | null = $state(null);

  const maxLogEntries = 1000;

  const filteredLogs = $derived.by(() => {
    return searchTerm
      ? logs.filter((log) =>
          log.message.toLowerCase().includes(searchTerm.toLowerCase()),
        )
      : logs;
  });

  function formatMessage(message: string): string {
    const urlRegex = /(https?:\/\/[^\s'"]+)/g;
    return message
      .replace(urlRegex, '<a class="anchor" href="$1" target="_blank">$1</a>')
      .replace(/\r?\n/g, "<br>");
  }

  function getLogClass(message: string): string {
    if (message.includes("[DEBUG]")) return "text-primary-500";
    if (message.includes("[INFO]")) return "text-success-500";
    if (message.includes("[WARNING]")) return "text-warning-500";
    if (message.includes("[ERROR]")) return "text-error-500";
    if (message.includes("[FATAL]")) return "text-error-950";
    return "text-primary-50";
  }

  function highlightText(
    text: string,
    searchTerm: string,
    logIndex: number,
  ): string {
    if (!searchTerm) return text;

    const regex = new RegExp(
      `(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );

    let matchCounter = 0;
    let cumulativeMatchIndex = 0;

    // Calculate the starting match index for this log entry
    for (let i = 0; i < logIndex; i++) {
      const matches = filteredLogs[i].message.match(regex);
      if (matches) {
        cumulativeMatchIndex += matches.length;
      }
    }

    return text.replace(regex, (match) => {
      const isCurrentMatch =
        cumulativeMatchIndex + matchCounter === currentMatchIndex;
      matchCounter++;

      if (isCurrentMatch) {
        return `<mark class="bg-primary-400 text-primary-900 ring-2 ring-primary-600">${match}</mark>`;
      } else {
        return `<mark class="bg-warning-200 text-warning-900">${match}</mark>`;
      }
    });
  }

  // Recalculate total match count across all filtered logs
  const totalMatchCount = $derived.by(() => {
    if (!searchTerm) return 0;

    let total = 0;
    const regex = new RegExp(
      `(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );

    filteredLogs.forEach((log) => {
      const matches = log.message.match(regex);
      if (matches) {
        total += matches.length;
      }
    });

    return total;
  });

  function toggleSearch() {
    searchVisible = !searchVisible;
    if (searchVisible) {
      setTimeout(() => searchInput?.focus(), 100);
    } else {
      searchTerm = "";
      currentMatchIndex = -1;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    // Ctrl+F to open search
    if (event.ctrlKey && event.key === "f") {
      event.preventDefault();
      toggleSearch();
    }

    if (event.key === "Escape" && searchVisible) {
      toggleSearch();
    }

    if (event.key === "Enter" && searchVisible && totalMatchCount > 0) {
      event.preventDefault();
      if (event.shiftKey) {
        currentMatchIndex =
          currentMatchIndex <= 0 ? totalMatchCount - 1 : currentMatchIndex - 1;
      } else {
        currentMatchIndex =
          currentMatchIndex >= totalMatchCount - 1 ? 0 : currentMatchIndex + 1;
      }
      scrollToMatch();
    }
  }

  function scrollToMatch() {
    if (currentMatchIndex >= 0 && currentMatchIndex < totalMatchCount) {
      const matchElements = logContainer.querySelectorAll("mark");
      if (matchElements[currentMatchIndex]) {
        matchElements[currentMatchIndex].scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    }
  }

  function clearSearch() {
    searchTerm = "";
    currentMatchIndex = -1;
  }

  EventsOn("summary-message", (summary: { summary_message: string }) => {
    summaryMessage = formatMessage(summary.summary_message);
  });

  EventsOn("add-summary-to-log", () => {
    addSummaryMessageToLog();
    summaryMessage = "";
  });

  function addSummaryMessageToLog() {
    if ("" === summaryMessage) {
      return;
    }
    logs.push({
      message: summaryMessage,
      html_class: "text-success-950",
    });
    summaryMessage = "";
  }

  EventsOn("log-message", (logMessage: LogMessage) => {
    let message = "";
    if (logMessage.level === "DEBUG") {
      const parts = [];
      if (logMessage.source_file) parts.push(logMessage.source_file);
      if (logMessage.function_name) parts.push(logMessage.function_name);
      if (logMessage.line_number) parts.push(String(logMessage.line_number));
      const debugInfo = parts.length > 0 ? ` (${parts.join("::")})` : "";

      message = `[${logMessage.level}]${debugInfo} ${formatMessage(logMessage.message)}`;
    } else {
      message = `[${logMessage.level}] ${formatMessage(logMessage.message)}`;
    }

    if (logs.length >= maxLogEntries) {
      logs.shift();
    }

    logs.push({
      message,
      html_class: logMessage.html_class ?? getLogClass(message),
    });
  });

  EventsOn("log-clear", () => {
    logs = logs.slice(0, 2);
  });

  let logContainer: HTMLDivElement;

  $effect(() => {
    if (logContainer && logs.length > 0 && !searchTerm) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  });

  // Reset search when logs change significantly
  $effect(() => {
    if (searchTerm && currentMatchIndex >= totalMatchCount) {
      currentMatchIndex = totalMatchCount > 0 ? 0 : -1;
    }
  });

  // Auto-scroll to current match when currentMatchIndex changes
  $effect(() => {
    if (searchTerm && currentMatchIndex >= 0 && totalMatchCount > 0) {
      // Small delay to ensure DOM is updated with new highlights
      setTimeout(() => scrollToMatch(), 50);
    }
  });
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flex min-h-6 flex-grow flex-col p-4">
  <div
    class="relative h-full flex-grow flex-col card bg-surface-100-900/50 p-4"
  >
    <!-- Search Bar -->
    {#if searchVisible}
      <div
        class="absolute top-2 right-2 z-10 flex items-center gap-2 rounded-lg border border-surface-300-700 bg-surface-200-800 p-2 shadow-lg"
      >
        <input
          bind:this={searchInput}
          bind:value={searchTerm}
          placeholder="Search logs..."
          class="w-48 border-none bg-transparent text-sm text-surface-900-100 outline-none"
          oninput={() => (currentMatchIndex = searchTerm ? 0 : -1)}
        />

        {#if searchTerm}
          <div class="text-xs whitespace-nowrap text-surface-600-400">
            {totalMatchCount > 0
              ? `${currentMatchIndex + 1}/${totalMatchCount}`
              : "0/0"}
          </div>

          <!-- Navigation buttons -->
          <button
            class="hover:bg-surface-300-600 rounded px-2 py-1 text-xs"
            disabled={totalMatchCount === 0}
            onclick={() => {
              currentMatchIndex =
                currentMatchIndex <= 0
                  ? totalMatchCount - 1
                  : currentMatchIndex - 1;
              scrollToMatch();
            }}
          >
            ↑ <!-- TODO: replace with SVG -->
          </button>
          <button
            class="hover:bg-surface-300-600 rounded px-2 py-1 text-xs"
            disabled={totalMatchCount === 0}
            onclick={() => {
              currentMatchIndex =
                currentMatchIndex >= totalMatchCount - 1
                  ? 0
                  : currentMatchIndex + 1;
              scrollToMatch();
            }}
          >
            ↓ <!-- TODO: replace with SVG -->
          </button>

          <button
            class="hover:bg-surface-300-600 rounded px-2 py-1"
            onclick={clearSearch}
          >
            <IconX size={12} />
          </button>
        {/if}

        <button
          class="hover:bg-surface-300-600 rounded px-2 py-1 text-xs"
          onclick={toggleSearch}
        >
          Close
        </button>
      </div>
    {/if}

    <div
      class="h-full flex-grow overflow-y-scroll font-mono break-words whitespace-normal select-text"
      bind:this={logContainer}
    >
      {#each searchTerm ? filteredLogs : logs as { message, html_class }, index}
        <div class={html_class}>
          {@html searchTerm
            ? highlightText(message, searchTerm, index)
            : message}
        </div>
      {/each}

      {#if searchTerm && filteredLogs.length === 0}
        <div class="py-4 text-center text-warning-500">
          No logs found matching "{searchTerm}"
        </div>
      {/if}
    </div>
  </div>
</div>
